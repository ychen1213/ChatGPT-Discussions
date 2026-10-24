from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parent
with np.load(p/'central_stripe_triangles.npz') as f:
    print('Triangles:',f['vertices_nm'].shape,f['faces'].shape,'XYZ bounds nm:',f['vertices_nm'].min(0),f['vertices_nm'].max(0))
with np.load(p/'central_stripe_voxels.npz') as f:
    print('Labels ZYX:',f['labels'].shape,'origin XYZ nm:',f['origin_xyz_nm'],'spacing nm:',f['spacing_nm'],'counts air/stripe/substrate:',np.bincount(f['labels'].ravel(),minlength=3))
with np.load(p/'central_stripe_splines.npz') as f:
    print('Spline coefficient shapes:',{k:f[k].shape for k in f.files if k.startswith('c')})
