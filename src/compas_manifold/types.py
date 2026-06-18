from typing import Annotated
from typing import List
from typing import Literal
from typing import Sequence
from typing import Tuple
from typing import Union

from numpy import float64
from numpy import int32
from numpy.typing import NDArray

FloatNx3 = Annotated[NDArray[float64], Literal["N", 3]]
IntNx3 = Annotated[NDArray[int32], Literal["N", 3]]
IntNx2 = Annotated[NDArray[int32], Literal["N", 2]]

VerticesNumpy = FloatNx3
"""An array of vertices, with each vertex defined by 3 spatial coordinates."""

FacesNumpy = IntNx3
"""An array of faces, with each face defined by 3 vertex indices."""

Vertices = Union[Sequence[Annotated[List[float], 3]], FloatNx3]
"""The vertices of a mesh, as an array-like sequence of 3-coordinate vertices."""

Faces = Union[Sequence[Annotated[List[int], 3]], IntNx3]
"""The faces of a mesh, as an array-like sequence of 3-index triangles."""

VerticesFaces = Tuple[Vertices, Faces]
"""Representation of a mesh as a tuple of vertices and faces."""

VerticesFacesNumpy = Tuple[FloatNx3, IntNx3]
"""Representation of a mesh as (V, F) numpy arrays: V is Nx3 float64, F is Mx3 int32."""

VerticesFacesSourceNumpy = Tuple[FloatNx3, IntNx3, IntNx2]
"""Representation of a boolean result with per-face source tracking. The third
array is Mx2: column 0 is the source mesh id (position in the input list),
column 1 is the original face index in that source mesh."""

IntNx1 = Annotated[NDArray[int32], Literal["N", 1]]

VerticesFacesPolygonsNumpy = Tuple[FloatNx3, IntNx3, IntNx1]
"""Representation of a boolean result with coplanar-face grouping. The third
array is Mx1: P[i] is the polygon (coplanar-face) id of output triangle i.
Triangles sharing an id form one planar n-gon face."""
