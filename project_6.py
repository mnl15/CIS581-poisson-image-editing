# -*- coding: utf-8 -*-
"""Project_6

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1dbjAKaRNnHy2qmvMi8TSHIUY8Y8mcXmj
"""

import scipy
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import scipy.sparse as sparse
from scipy.sparse.linalg import spsolve
import scipy.signal as signal
from google.colab import files

uploaded = files.upload()

def getIndexes(mask, targetH, targetW, offsetX=0, offsetY=0):
    """ Creates indexes in the target image, each replacement pixel in the
    target image would get index starting from 1, other pixels get 0 in the indexes.

    Args:
    mask: SrcH * SrcW, logical mask of source image
    targetH, targetW: int, height and width of target image
    offsetX, offsetY: int, offset of replacement pixel area from source to target

    Return:
    indexes: targetH * targetW, indexes of target image
    """
    # IMPLEMENT HERE
    x, y = np.meshgrid(np.arange(mask.shape[1]), np.arange(mask.shape[0]))
    target_x, target_y = x[mask > 0], y[mask > 0]
    indexes = np.zeros((targetH, targetW), dtype=np.int32)
    indexes[target_y + offsetY, target_x + offsetX] = np.arange(1, len(target_x)+1)
    return indexes

def getCoefficientMatrix(indexes):
  """
  constructs the coefficient matrix(A in Ax=b)
  
  Args: 
  indexes: targetH * targetW, indexes of target image starting from 1, 0 if not in target area 
  
  returns:
  coeffA: N * N(N is max index), a matrix corresponds to laplacian kernel, 4 on the diagonal and -1 for each neighbor
  """
  # IMPLEMENT HERE
  Y, X = np.nonzero(indexes)
  # get indexes for 4 values 
  row = np.arange(0, len(Y))
  col = np.arange(0, len(Y))
  data = 4 * np.ones(len(Y))
  # get indexes for -1 values 
  N = np.count_nonzero(indexes)
  left = np.zeros(N, dtype=np.int32)
  valid = X - 1 >= 0
  left[valid] = indexes[Y[valid], (X - 1)[valid]]
  right = np.zeros(N, dtype=np.int32)
  valid = X + 1 < len(indexes[0])
  right[valid] = indexes[Y[valid], (X + 1)[valid]]
  up = np.zeros(N, dtype=np.int32)
  valid = Y - 1 >= 0
  up[valid] = indexes[(Y - 1)[valid], X[valid]]
  down = np.zeros(N, dtype=np.int32)
  valid = Y + 1 < len(indexes)
  down[valid] = indexes[(Y + 1)[valid], X[valid]]  
  all = [left, right, up, down]
  for a in all: 
    vals = np.arange(1, len(Y) + 1)
    valid = np.logical_and(a, vals>0)
    vals = [vals[i] - 1 for i in range(len(valid)) if valid[i] == True]
    a = [a[i] - 1 for i in range(len(valid)) if valid[i] == True]
    valid = -1 * np.ones(len(vals))
    row = np.concatenate((row, vals))
    col = np.concatenate((col, a))
    data = np.concatenate((data, valid))
  
  # create coefficient matrix 
  return scipy.sparse.csr_matrix( (data,(row,col)) )
  # the coefficient matrix is by nature sparse. consider using scipy.sparse.csr_matrixr

def getSolutionVect(indexes, source, target, offsetX, offsetY):
    """
    constructs the target solution vector(b in Ax=b) 
    
    Args:
    indexes:  targetH * targetW, indexes of replacement area
    source, target: source and target image
    offsetX, offsetY: offset of source image origin in the target image

    Returns:
    solution vector b (for single channel)
    """
    # IMPLEMENT HERE
    # 1. get Laplacian part of b from source image
    laplacian = np.array([[0, -1, 0], 
                          [-1, 4, -1],
                          [0, -1, 0]])
    
    source_laplacian = signal.convolve2d(source, laplacian, 'same')
    
    # 2. get pixel part of b from target image
    w, h = target.shape[1], target.shape[0]
    x, y = np.meshgrid(np.arange(w), np.arange(h))

    x_left = (x-1).clip(0, w-1)
    left = target[y, x_left]
    indexes_left = indexes[y, x_left]

    x_right = (x+1).clip(0, w-1)
    right = target[y, x_right]
    indexes_right = indexes[y, x_right]

    y_up = (y-1).clip(0, h-1)
    up = target[y_up, x]
    indexes_up = indexes[y_up, x]

    y_down = (y+1).clip(0, h-1)
    down = target[y_down, x]
    indexes_down = indexes[y_down, x]

    # 3. add two parts together to get 
    Y, X = np.nonzero(indexes)
    N = np.count_nonzero(indexes)
    b = np.zeros((1, N))

    for (j, i) in list(zip(Y, X)):
      val = source_laplacian[j - offsetY, i - offsetX]
      if indexes_left[j,i] == 0:
        val += left[j,i]
      if indexes_right[j,i] == 0:
        val += right[j,i]
      if indexes_up[j,i] == 0:
        val += up[j,i]
      if indexes_down[j,i] == 0:
        val += down[j,i]
      
      b[0][indexes[j][i]-1] = val

    return b

def solveEqu(A, b):
  """
  solve the equation Ax = b to get replacement pixels x in the replacement area
  Note: A is a sparse matrix, so we need to use coresponding function to solve it

  Args:
  - A: Laplacian coefficient matrix
  - b: target solution vector
  
  Returns:
  - x: solution of Ax = b
  """
  # IMPLEMENT HERE
  return spsolve(A, b)

def reconstructImg(indexes, red, green, blue, targetImg):
    """
    reconstruct the target image with new red, green, blue channel values in th
    e indexes area

    red, green, blue: 1 x N, three chanels for replacement pixels
    """
    # 1. get nonzero component in indexes
    Y, X = np.nonzero(indexes)

    # 2. stack three channels together with numpy dstack
    newValues = np.dstack((red, green, blue))

    # 3. copy new pixels in the indexes area to the target image 
    # use numpy copy to make a copy of targetImg, otherwise the original targetImg might change, too
    copyImg = np.copy(targetImg)

    print(newValues.shape)
    print(copyImg.shape)

    for (j, i) in list(zip(Y, X)):
      for z in range(3):
        copyImg[j][i][z] = newValues[0][int(indexes[j][i]-1)][z]

    return copyImg

"""
Function (do not modify)
"""
def seamlessCloningPoisson(sourceImg, targetImg, mask, offsetX, offsetY):
    """
    Wrapper function to put all steps together
    Args:
    - sourceImg, targetImg: source and targe image
    - mask: masked area in the source image
    - offsetX, offsetY: offset of the mask in the target image
    Returns:
    - ResultImg: result image
    """
    # step 1: index replacement pixels
    indexes = getIndexes(mask, targetImg.shape[0], targetImg.shape[1], offsetX,
                         offsetY)
    # step 2: compute the Laplacian matrix A
    A = getCoefficientMatrix(indexes)

    # step 3: for each color channel, compute the solution vector b
    red, green, blue = [
        getSolutionVect(indexes, sourceImg[:, :, i], targetImg[:, :, i],
                        offsetX, offsetY).T for i in range(3)
    ]

    # step 4: solve for the equation Ax = b to get the new pixels in the replacement area
    new_red, new_green, new_blue = [
        solveEqu(A, channel)
        for channel in [red, green, blue]
    ]

    # step 5: reconstruct the image with new color channel
    resultImg = reconstructImg(indexes, new_red, new_green, new_blue,
                               targetImg)
    return resultImg

"""
Script (do not modify)
"""
src_path = 'source_3.jpg'
src = np.array(Image.open(src_path).convert('RGB'), 'f') / 255
target_path  ='target_3.jpg'
target = np.array(Image.open(target_path).convert('RGB'), 'f') / 255
offsetX = 40
offsetY = 20
mask_path = 'mask_3.bmp'
mask = np.array(Image.open(mask_path)) > 0
result = seamlessCloningPoisson(src, target, mask, offsetX, offsetY)
plt.imshow(result)
plt.show()
cloned = Image.fromarray((np.clip(result, 0, 1) * 255).astype(np.uint8))
cloned.save('cloned.png')
files.download('cloned.png')

def getSolutionVectMixing(indexes, source, target, offsetX, offsetY):
    """
    constructs the target solution vector(b in Ax=b) 
    
    Args:
    indexes:  targetH * targetW, indexes of replacement area
    source, target: source and target image
    offsetX, offsetY: offset of source image origin in the target image

    Returns:
    solution vector b (for single channel)
    """
    # IMPLEMENT HERE
    # 1. get Laplacian part of b from source image
    laplacian = np.array([[0, -1, 0], 
                          [-1, 4, -1],
                          [0, -1, 0]])
    
    source_laplacian = signal.convolve2d(source, laplacian)
    target_laplacian = signal.convolve2d(target, laplacian)
    
    # 2. get pixel part of b from target image
    w, h = target.shape[1], target.shape[0]
    x, y = np.meshgrid(np.arange(w), np.arange(h))

    x_left = (x-1).clip(0, w-1)
    left = target[y, x_left]
    indexes_left = indexes[y, x_left]

    x_right = (x+1).clip(0, w-1)
    right = target[y, x_right]
    indexes_right = indexes[y, x_right]

    y_up = (y-1).clip(0, h-1)
    up = target[y_up, x]
    indexes_up = indexes[y_up, x]

    y_down = (y+1).clip(0, h-1)
    down = target[y_down, x]
    indexes_down = indexes[y_down, x]

    # 3. add two parts together to get 
    Y, X = np.nonzero(indexes)
    N = np.count_nonzero(indexes)
    b = np.zeros((1, N))

    for (j, i) in list(zip(Y, X)):
      if np.abs(source_laplacian[j-offsetY, i-offsetX]) >= np.abs(target_laplacian[j][i]):
        val = source_laplacian[j-offsetY, i-offsetX]
      else:
        val = target_laplacian[j][i]

      if indexes_left[j,i] == 0:
        val += left[j,i]
      if indexes_right[j,i] == 0:
        val += right[j,i]
      if indexes_up[j,i] == 0:
        val += up[j,i]
      if indexes_down[j,i] == 0:
        val += down[j,i]
      
      b[0][indexes[j][i]-1] = val

    return b

"""
Function (do not modify)
"""
def PoissonMixing(sourceImg, targetImg, mask, offsetX, offsetY):
    """
    Wrapper function to put all steps together
    Args:
    - sourceImg, targetImg: source and target image
    - mask: masked area in the source image
    - offsetX, offsetY: offset of the mask in the target image
    Returns:
    - ResultImg: result image
    """
    # step 1: index replacement pixels
    indexes = getIndexes(mask, targetImg.shape[0], targetImg.shape[1], offsetX,
                         offsetY)
    # step 2: compute the Laplacian matrix A
    A = getCoefficientMatrix(indexes)

    # step 3: for each color channel, compute the solution vector b
    red, green, blue = [
        getSolutionVectMixing(indexes, sourceImg[:, :, i], targetImg[:, :, i],
                        offsetX, offsetY).T for i in range(3)
    ]

    # step 4: solve for the equation Ax = b to get the new pixels in the replacement area
    new_red, new_green, new_blue = [
        solveEqu(A, channel)
        for channel in [red, green, blue]
    ]

    # step 5: reconstruct the image with new color channel
    resultImg = reconstructImg(indexes, new_red, new_green, new_blue,
                               targetImg)
    return resultImg

"""
Script (do not modify)
"""
src_path = 'source_2.jpg'
src = Image.open(src_path).convert('RGB')

src = np.array(src, 'f') / 255
target_path  ='target_2.jpg'
target = Image.open(target_path).convert('RGB')
target = np.array(target, 'f') / 255
offsetX = 10
offsetY = 130
mask_path = 'mask_2.bmp'
mask = Image.open(mask_path)
mask =np.array(mask) > 0
result = PoissonMixing(src, target, mask, offsetX, offsetY)
plt.imshow(result)
plt.show()
mixed = Image.fromarray((np.clip(result, 0, 1) * 255).astype(np.uint8))
mixed.save('mixed.png')
files.download('mixed.png')

def getSolutionVectTexture(indexes, target, mask, edges):
    """
    constructs the target solution vector(b in Ax=b) 
    
    Args:
    indexes:  targetH * targetW, indexes of replacement area
    source, target: source and target image
    offsetX, offsetY: offset of source image origin in the target image

    Returns:
    solution vector b (for single channel)
    """
    # IMPLEMENT HERE
    # 1. get Laplacian part of b from source image    
    # 2. get pixel part of b from target image
    w, h = target.shape[1], target.shape[0]
    x, y = np.meshgrid(np.arange(w), np.arange(h))

    x_left = (x-1).clip(0, w-1)
    left = target[y, x_left]
    indexes_left = indexes[y, x_left]

    x_right = (x+1).clip(0, w-1)
    right = target[y, x_right]
    indexes_right = indexes[y, x_right]

    y_up = (y-1).clip(0, h-1)
    up = target[y_up, x]
    indexes_up = indexes[y_up, x]

    y_down = (y+1).clip(0, h-1)
    down = target[y_down, x]
    indexes_down = indexes[y_down, x]

    # 3. add two parts together to get 
    Y, X = np.nonzero(indexes)
    N = np.count_nonzero(indexes)
    b = np.zeros((1, N))

    for (j, i) in list(zip(Y, X)):
      val = 0
      if edges[j][i] == 1:
        val += 4 * target[j][i] - target[j-1][i] - target[j+1][i] - target[j][i-1] - target[j][i+1]
      else:
        if edges[j][i-1] == 1:
          val += target[j][i] - target[j][i-1]
        if edges[j][i+1] == 1:
          val += target[j][i] - target[j][i+1]
        if edges[j-1][i] == 1:
          val += target[j][i] - target[j-1][i]
        if edges[j+1][i] == 1:
          val += target[j][i] - target[j+1][i]

      if indexes_left[j,i] == 0:
        val += left[j,i]
      if indexes_right[j,i] == 0:
        val += right[j,i]
      if indexes_up[j,i] == 0:
        val += up[j,i]
      if indexes_down[j,i] == 0:
        val += down[j,i]
      
      b[0][indexes[j][i]-1] = val

    return b

"""
Function (do not modify)
"""
def PoissonTextureFlattening(targetImg, mask, edges):
    """
    Wrapper function to put all steps together
    Args:
    - targetImg: target image
    - mask: masked area in the source image
    - offsetX, offsetY: offset of the mask in the target image
    Returns:
    - ResultImg: result image
    """
    # step 1: index replacement pixels
    indexes = getIndexes(mask, targetImg.shape[0], targetImg.shape[1])
    # step 2: compute the Laplacian matrix A
    A = getCoefficientMatrix(indexes)

    # step 3: for each color channel, compute the solution vector b
    red, green, blue = [
        getSolutionVectTexture(indexes, targetImg[:, :, i], mask, edges).T for i in range(3)
    ]

    # step 4: solve for the equation Ax = b to get the new pixels in the replacement area
    new_red, new_green, new_blue = [
        solveEqu(A, channel)
        for channel in [red, green, blue]
    ]

    # step 5: reconstruct the image with new color channel
    resultImg = reconstructImg(indexes, new_red, new_green, new_blue,
                               targetImg)
    return resultImg

"""
Script (do not modify)
"""
target_path  ='bean.jpg'
target = np.array(Image.open(target_path).convert('RGB'), 'f') / 255
from skimage.color import rgb2gray
from skimage import feature
edges = feature.canny(rgb2gray(target))
plt.imshow(edges)
plt.show()
mask_path = 'mask_bean.bmp'
mask = np.array(Image.open(mask_path)) > 0
result = PoissonTextureFlattening(target, mask, edges)
plt.imshow(result)
plt.show()
flatten = Image.fromarray((np.clip(result, 0, 1) * 255).astype(np.uint8))
flatten.save('flatten.png')
files.download('flatten.png')