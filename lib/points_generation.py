import ghalton
import copy
import numpy as np
import scipy.stats as st


def boundary_generation(n_boundary):
    xb = []
    yb = []

    for val in np.linspace(0., 1., n_boundary+1)[0:-1]:
        xb.append(val)
        yb.append(0.)
    for val in np.linspace(0., 1., n_boundary+1)[0:-1]:
        xb.append(1.)
        yb.append(val)
    for val in np.linspace(0., 1., n_boundary+1)[::-1][:-1]:
        xb.append(val)
        yb.append(1.)
    for val in np.linspace(0., 1., n_boundary+1)[::-1][:-1]:
        xb.append(0.)
        yb.append(val)
    xb = np.asarray(xb)
    yb = np.asarray(yb)
    boundary_points = np.vstack([xb,yb]).T
    return boundary_points


def _inv_gaussian_kernel(kernlen=3, sig=0.1):
    """
    Returns a 2D Gaussian kernel array.
    """
    interval = (2*sig+1.)/(kernlen)
    x = np.linspace(-sig-interval/2., sig+interval/2., kernlen+1)
    kern1d = np.diff(st.norm.cdf(x))
    kernel_raw = np.sqrt(np.outer(kern1d, kern1d))
    kernel = kernel_raw/kernel_raw.sum()
    return kernel.max()-kernel


def random_centers_generation(data, n_centers, base_level=None, power=2., umask=None):
    # fixed seed
    np.random.seed(0)

    # for safety reasons
    data = copy.deepcopy(data)

    # unusable pixels mask
    if base_level is not None:
        mask = data <= base_level
        if umask is not None:
            mask = np.logical_or(mask, umask)
        if isinstance(mask, np.ma.masked_array):
            mask.fill_value = True
            mask = mask.filled()
        if np.sum(~mask) < n_centers:
            print('The number of usable pixels is less than n_centers')
            return None

    # applying power and re-normalizing
    data **= power
    data /= data.max()

    # data cube dimensions
    m,n = data.shape
    
    # center points positions
    x = np.linspace(0., 1., m+2, endpoint=True)[1:-1]
    y = np.linspace(0., 1., n+2, endpoint=True)[1:-1]
    X,Y  = np.meshgrid(x, y, indexing='ij')
    points_positions = np.vstack( [ X.ravel(), Y.ravel() ]).T
    
    # array with indexes of such centers
    points_indexes = np.arange(0, points_positions.shape[0])
    
    # array with probabilities of selection for each center
    if isinstance(data, np.ma.masked_array):
        data.fill_value = 0.
        data = data.filled()
    if isinstance(mask, np.ndarray):
        data[mask] = 0.
        prob = data/data.sum()
    else:
        prob = data/data.sum()
    
    # convolution kernel
    #K = np.array([[0.5, 0.5, 0.5], [0.5, 0., 0.5], [0.5, 0.5, 0.5]])
    K = _inv_gaussian_kernel(kernlen=3, sig=3.)
    
    selected = []
    while len(selected)!=n_centers:
        sel = np.random.choice(points_indexes, size=1 , p=prob.ravel(), replace=False)[0]
        # border pixels can't be selected
        index0 = sel / m
        index1 = sel % n
        if index0==0 or index0==m-1 or index1==0 or index1==n-1: continue
        selected.append(sel)
        # update the pixel probabilities array
        prob[index0-1:index0+2, index1-1:index1+2] *= K
        #prob[index0, index1] = 0.
        prob /= prob.sum()
        
    return points_positions[selected]


def qrandom_centers_generation(dfunc, n_centers, base_level, ndim=2, get_size=50, umask=None):
    # generating the sequencer
    sequencer = ghalton.Halton(ndim)

    points_positions = []
    n_selected = 0

    while True:
        points = np.asarray(sequencer.get(get_size))
        values = dfunc(points)

        for i in range(get_size):
            if values[i] > base_level:
                points_positions.append(points[i])
                n_selected += 1
            if n_selected == n_centers:
                return np.asarray(points_positions)


def boundary_map(data, base_level):
    pixel_map = data > base_level
    m,n = pixel_map.shape
    border_map = np.zeros((m,n), dtype=bool)
    for i in range(m):
        for j in range(n):
            # just verify valid pixels
            if pixel_map[i,j]==False: continue
            for p in range(-1,2):
                for q in range(-1,2):
                    if p==q==0: continue
                    if i+p < 0 or j+q < 0: continue
                    if i+p >= m or j+q >= n: continue
                    # in case pixel_map[i,j] has a unusable neighbor pixel
                    # then pixel_map[i,j] is a border pixel
                    if pixel_map[i+p,j+q]==False: border_map[i,j] = True
    return border_map


def boundary_points_generation(data, base_level, n_points):
    border_map = boundary_map(data, base_level)
    x_pos, y_pos = np.where(border_map)
    # mapping to [0,1] range
    x_pos = x_pos.astype(float)
    y_pos = y_pos.astype(float)
    x_pos /= float(data.shape[0]); x_pos += 0.5/data.shape[0]
    y_pos /= float(data.shape[1]); y_pos += 0.5/data.shape[1]
    boundary_points =  np.vstack([x_pos, y_pos]).T
    # random selecting the specified number of points
    if n_points > boundary_points.shape[0]:
        print("Number of can't be greater than the number of border pixels")
        return None
    np.random.seed(0)
    points_indexes = np.arange(boundary_points.shape[0])
    selected = np.random.choice(points_indexes, size=n_points)
    return boundary_points[selected]