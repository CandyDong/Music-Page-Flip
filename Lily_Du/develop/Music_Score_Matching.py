import os
from os import walk
from wand.image import Image
from skimage.measure import compare_ssim
import imutils
import cv2
import numpy as np
import pytesseract

# This function converts a pdf into an image format
def convertPdfToImage(file, outputPath):
    name = '_'.join(file.split('/')[-1].split('.')[:-1])
    try:
        with Image(filename=file) as img:
            with img.convert('jpeg') as converted:
                os.mkdir(outputPath+'/'+name)
                converted.save(filename=outputPath+'/'+name+'/'+name+'.jpeg')
        print(file+' successfully converted to jpeg')
    except Exception as e:
        print(file+' failed to convert due to:')
        print(e)
    print('\n')
    return outputPath+'/'+name


# Get the input file that needs to be parsed (music score picture taken with phone)
def getTargetFile(rootPath):
    files = []
    for (dirpath, dirnames, filenames) in walk(rootPath):
        for filename in filenames:
            files.append(dirpath+'/'+filename)
    return files

# Get the input image that user uploads to database
def getInputImg(inputPath):
    for (dirpath, dirnames, filenames) in walk(inputPath):
        for filename in filenames:
            if('jpeg' in filename.lower()):
                return dirpath+'/'+filename


def checkDiff(inputImg, comparePath):
    compareImg = comparePath+'/'+comparePath.split('/')[-1]+'-0.jpeg'
    
    # load the two input images
    imageA = cv2.imread(inputImg)
    imageB = cv2.imread(compareImg)

    imageA = cv2.resize(imageA, (imageB.shape[1], imageB.shape[0]), interpolation = cv2.INTER_AREA)
    
    # convert the images to grayscale
    grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
    # cv2.imwrite('grayA.png', grayA)
    # cv2.imwrite(comparePath+'grayB.png', grayB)

    # crop the title of music scores
    cropA = grayA[:30, :]
    cropB = grayB[:60, :]

    # Add padding around the smaller image to make them the same shape
    pad_A = cv2.copyMakeBorder(cropA, 0, cropB.shape[0]-cropA.shape[0], 0, 0, cv2.BORDER_CONSTANT,
    value=[255, 255, 255])

    cv2.imwrite('../static/input/cropA.png', pad_A)
    cv2.imwrite('../static/input/cropB.png', cropB)

    
    return mse(pad_A, cropB)

def ssim(imageA, imageB):
    # compute the Structural Similarity Index (SSIM) between the two
    # images, ensuring that the difference image is returned
    (score, diff) = compare_ssim(grayA, grayB, full=True)
    diff = (diff * 255).astype("uint8")
    print("SSIM: {}".format(score))

    return score, diff

def mse(imageA, imageB):
    # the 'Mean Squared Error' between the two images is the
    # sum of the squared difference between the two images;
    # NOTE: the two images must have the same dimension
    err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
    err /= float(imageA.shape[0] * imageA.shape[1])
    
    # return the MSE, the lower the error, the more "similar"
    # the two images are
    return err


def main():
    rootPath = '../static/scores'
    outputPath = '../static/images'
    inputPath = '../static/input'

    # Get scores from database
    files = getTargetFile(rootPath)
    print('Got pdf scores from database')
    
    # Convert the scores from database to images and return path to that image folder
    imagesPath = []
    for file in files:
        imagesPath.append(convertPdfToImage(file, outputPath))
    print('pdf scores converted to jpeg files')


    # Get the input image
    inputImg = getInputImg(inputPath)
    print(inputImg + ' get from input folder')

    # # Check which score in database the input matches to and return its name
    # differences = []
    # for imagePath in imagesPath:
    #     try:
    #         difference = checkDiff(inputImg, imagePath)
    #         print(imagePath, difference)
    #     except Exception as e:
    #         print(e)



main()