"""Lunar Dig LD-Field tile format 1, deterministic Merkle field packaging.
This module never generates actual lunar measurements. Synthetic fixtures are TEST ONLY.
"""
import hashlib, json, struct, pathlib, math
from dataclasses import dataclass

MAGIC=b'LDFT'; TILE_LEN=8946; CELLS=625; NODATA=65535
LAYERS=('elevation','slope','cold_trap','sunlight','tio2','tio2_error','usable')
ZONES=tuple([f'ltm-{i}-{h}' for h in ('n','s') for i in range(1,46)]+['lps-n','lps-s'])

def H(domain: str, payload: bytes)->bytes:
    return hashlib.sha256(domain.encode()+b'\0'+len(payload).to_bytes(8,'big')+payload).digest()

def node_hash(left: bytes,right: bytes)->bytes:
    value=b'{"left":"'+left.hex().encode()+b'","right":"'+right.hex().encode()+b'"}'
    return H('ld.field.node.v0',value)

def key_bytes(key):
    return struct.pack('<HHH',*key)

def get_bit(bits,i): return bool(bits[i>>3] & (1<<(i&7)))
def set_bit(bits,i): bits[i>>3]|=1<<(i&7)

@dataclass
class Tile:
    zone:int
    tile_e:int
    tile_n:int
    whole:bytes
    inzone:bytes
    coarse:tuple
    layers:tuple
    def encode(self):
        if not (0<=self.zone<92 and 0<=self.tile_e<=65535 and 0<=self.tile_n<=65535):raise ValueError('bad tile key')
        if len(self.whole)!=79 or len(self.inzone)!=79 or len(self.coarse)!=6 or len(self.layers)!=7: raise ValueError('invalid tile shape')
        if any(len(a)!=CELLS for a in self.layers): raise ValueError('invalid layer size')
        for i in range(CELLS):
            if get_bit(self.whole,i) and not get_bit(self.inzone,i): raise ValueError('whole outside zone')
            if not get_bit(self.inzone,i) and any(layer[i]!=(-32768 if k==0 else NODATA) for k,layer in enumerate(self.layers)):
                raise ValueError('out-of-zone cell has values')
        head=struct.pack('<4sHHHHH10x6H',MAGIC,1,self.zone,self.tile_e,self.tile_n,sum(int.bit_count(x) for x in self.whole),*self.coarse)
        body=b''.join(struct.pack('<625'+('h' if k==0 else 'H'),*self.layers[k]) for k in range(7))
        data=head+self.whole+b'\0'+self.inzone+b'\0'+body
        if len(data)!=TILE_LEN:raise AssertionError(len(data))
        return data
    @staticmethod
    def decode(data:bytes, expected=None):
        if len(data)!=TILE_LEN:raise ValueError('tile length')
        magic,fmt,z,e,n,count=struct.unpack_from('<4sHHHHH',data)
        if magic!=MAGIC or fmt!=1:raise ValueError('tile magic/format')
        if z>=92:raise ValueError('zone')
        if data[14:24]!=bytes(10) or data[115] or data[195]:raise ValueError('reserved/padding')
        whole=data[36:115]; inzone=data[116:195]
        if whole[-1]&0xfe or inzone[-1]&0xfe:raise ValueError('bitmap padding bits')
        if sum(int.bit_count(x) for x in whole)!=count:raise ValueError('whole count')
        if any(a&~b for a,b in zip(whole,inzone)):raise ValueError('whole outside zone')
        if expected is not None and (z,e,n)!=tuple(expected):raise ValueError('tile key')
        layers=tuple(struct.unpack_from('<625'+('h' if k==0 else 'H'),data,196+1250*k) for k in range(7))
        coarse=struct.unpack_from('<6H',data,24)
        tile=Tile(z,e,n,whole,inzone,coarse,layers)
        for i in range(CELLS):
            if not get_bit(inzone,i) and any(layer[i]!=(-32768 if k==0 else NODATA) for k,layer in enumerate(layers)):
                raise ValueError('out-of-zone data')
        return tile

def synthetic_tile(zone,e,n):
    """Synthetic demonstration values, NOT NASA/USGS data or surveyed parcels."""
    whole=bytearray(79); iz=bytearray(79)
    layers=[[0]*CELLS for _ in range(7)]
    seed=(zone*97+e*29+n*13)
    for i in range(CELLS):
        x=i%25; y=i//25
        inside=(x!=24 or y%7!=0) # deliberately partial synthetic fringe
        complete=inside and not (y==24 and x%9==0)
        if inside:set_bit(iz,i)
        if complete:set_bit(whole,i)
        if not inside:
            for k in range(7):layers[k][i]=(-32768 if k==0 else NODATA)
            continue
        layers[0][i]=round(200*math.sin((x+seed)/9)+120*math.cos((y+seed)/11))
        layers[1][i]=int(400+1100*abs(math.sin((x+y+seed)/18)))
        layers[2][i]=int(10000*max(0,0.14+0.14*math.sin((x+seed)/8))) if zone>=90 else 0
        layers[3][i]=int(10000*(0.76+0.19*abs(math.sin((x+y+seed)/18)))) if zone>=90 else 5000
        layers[4][i]=int(300+350*abs(math.sin((x+seed)/13))) if zone<90 else NODATA
        layers[5][i]=NODATA # source error unresolved
        layers[6][i]=int(10000*(0.45+0.5*abs(math.cos((x+y+seed)/21))))
    return Tile(zone,e,n,bytes(whole),bytes(iz),(1400,65535,450,65535,65535,65535),tuple(tuple(a) for a in layers))

def make_tree(leaves):
    levels=[list(leaves)]
    if not levels[0]:raise ValueError('empty field')
    while len(levels[-1])>1:
        prior=levels[-1]
        levels.append([node_hash(prior[i],prior[i+1]) if i+1<len(prior) else prior[i] for i in range(0,len(prior),2)])
    return levels

def proof(levels,index):
    siblings=[]; i=index
    for level in levels[:-1]:
        other=i^1
        if other<len(level):siblings.append(level[other].hex())
        i//=2
    return siblings

def verify_proof(tile:bytes, index:int,total:int,siblings,root:str):
    if not (0<=index<total):return False
    h=H('ld.field.tile.v0',tile); length=total; i=index; k=0
    while length>1:
        other=i^1
        if other<length:
            if k>=len(siblings) or len(siblings[k])!=64:return False
            try:other_hash=bytes.fromhex(siblings[k]); k+=1
            except ValueError:return False
            h=node_hash(h,other_hash) if i%2==0 else node_hash(other_hash,h)
        i//=2; length=(length+1)//2
    return k==len(siblings) and h.hex()==root

def package(tiles, destination, version='synthetic-v1'):
    out=pathlib.Path(destination); out.mkdir(parents=True,exist_ok=True)
    tiles=sorted(tiles,key=lambda t:(t.zone,t.tile_e,t.tile_n))
    keys=[(t.zone,t.tile_e,t.tile_n) for t in tiles]
    if len(set(keys))!=len(keys):raise ValueError('duplicate tile')
    index=b''.join(key_bytes(k) for k in keys)
    leaves=[]
    for t in tiles:
        data=t.encode(); Tile.decode(data,(t.zone,t.tile_e,t.tile_n))
        filename=out/'tiles'/ZONES[t.zone]/f'{t.tile_e}-{t.tile_n}.ldft'
        filename.parent.mkdir(parents=True,exist_ok=True); filename.write_bytes(data)
        leaves.append(H('ld.field.tile.v0',data))
    levels=make_tree(leaves)
    (out/'index.bin').write_bytes(index)
    (out/'tree.bin').write_bytes(b''.join(h for level in levels for h in level))
    (out/'labels.bin').write_bytes(b'\0'*8*len(tiles))
    (out/'overview').mkdir(exist_ok=True)
    field={'format':1,'version':version,'synthetic':True,'source_status':'SYNTHETIC TEST ONLY; NOT LUNAR SURVEY DATA',
           'field_root':levels[-1][0].hex(),'index_hash':H('ld.field.index.v0',index).hex(),
           'tile_count':len(tiles),'tile_size':TILE_LEN,'source_products':[],
           'pipeline_commit':None,'environment_digest':None,
           'layer_table':list(LAYERS),'keys':[list(k) for k in keys],
           'counts':{'whole':sum(sum(int.bit_count(x) for x in t.whole) for t in tiles),
                     'in_zone':sum(sum(int.bit_count(x) for x in t.inzone) for t in tiles)}}
    (out/'field.json').write_text(json.dumps(field,indent=2,sort_keys=True)+'\n')
    # PINNED TRUST ANCHOR must be distributed separately from the data host.
    anchor={'field_root':field['field_root'],'index_hash':field['index_hash'],'tile_count':len(tiles),'version':version}
    return field,anchor

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output');args=p.parse_args()
    field,anchor=package([synthetic_tile(22,10,38),synthetic_tile(22,10,39),synthetic_tile(91,19,19),synthetic_tile(91,19,20),synthetic_tile(91,20,19)],args.output)
    print(json.dumps(anchor,indent=2))
