import os
from os import walk
from wand.image import Image
import PIL
# from skimage.measure import compare_ssim
# import imutils
import cv2
import numpy as np
import pytesseract
from fuzzywuzzy import fuzz
import time
import json

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

def getTitle(inputImg):
    image = cv2.imread(inputImg)
    copy = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    # find contours
    (contours, _) = cv2.findContours(~gray,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE) 

    for contour in contours:
        """
        draw a rectangle around those contours on main image
        """
        [x,y,w,h] = cv2.boundingRect(contour)
        cv2.rectangle(copy, (x,y), (x+w,y+h), (0, 255, 0), 1)
    cv2.imwrite('contours.png', copy)

    # create blank image of same dimension of the original image
    mask = np.ones(copy.shape[:2], dtype="uint8") * 255 

    # Collecting y value of each contour
    (contours, _) = cv2.findContours(~gray,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE) 

    ys = []
    for c in contours:
        [x,y,w,h] = cv2.boundingRect(c)
        ys.append(y)
    ys.sort()

    # Get the y value of possible title positions, 
    # requires the black space above music score to be narrow
    # threshold 20px difference between starting position of all words of a title
    accepted_ys = []
    for i in range(len(ys)):
        if i == 0:
            accepted_ys.append(ys[i])
        else:
            if(ys[i] - ys[i-1] <= 20):
                accepted_ys.append(ys[i])
            else:
                break
    
    for c in contours:
        [x,y,w,h] = cv2.boundingRect(c)
        if y in accepted_ys:
            cv2.drawContours(mask, [c], -1, 0, -1)

    filename = "{}.png".format(os.getpid())
    cv2.imwrite(filename, mask)
    # load the image as a PIL/Pillow image, apply OCR, and then delete
    # the temporary file
    text = pytesseract.image_to_string(PIL.Image.open(filename))
    os.remove(filename)
    print(text)
    # show the output images
    cv2.imwrite("Image.png", image)
    cv2.imwrite("Output.png", gray)
    return text

def getDBTitles(rootPath):
    DBScoreTitles = []
    for (dirpath, dirnames, filenames) in walk(rootPath):
        for filename in filenames:
            if(filename.endswith('.pdf')):
                print(filename)
                DBScoreTitles.append(filename.replace('.pdf', ''))
    return DBScoreTitles


def matchTitle(inputTitle, L):
    maxRatio = 0
    scoreTitle = None
    for title in L:
        ratio = fuzz.partial_ratio(inputTitle, title)
        if(ratio > maxRatio):
            maxRatio = ratio
            scoreTitle = title
    return scoreTitle


def findFlipPoint(files):
    inputFolder = "../../static/preprocessed_inputs/"
    outputFolder = "../../static/preprocessed_outputs/"

    for file in files:
        if(file.endswith('.pdf')):
            filename = file.split('/')[-1].strip(".pdf")
            subfolderName = inputFolder+filename
            noteCount = 0
            outputDict = dict()
            for (dirpath, dirnames, filenames) in walk(subfolderName):
                for posfile in filenames:
                    if('positions' in posfile):
                        if(noteCount != 0):
                            if('page' in outputDict):
                                outputDict['page'].append(noteCount)
                            else:
                                outputDict['page'] = [noteCount]
                        positionsFile = open(dirpath+'/'+posfile, "r")
                        lines = positionsFile.readlines()
                        notePos = []
                        startPos = []
                        OnePos = []
                        TwoPos = []
                        noteStaffPos = []
                        staffCount = 0
                        for prim in lines:
                            if 'note' in prim:
                                noteCount += 1
                                (primType, x, y) = prim.strip().split(',')
                                noteStaffPos.append((int(x), int(y)))
                            elif 'start' in prim:
                                (primType, x, y) = prim.strip().split(',')
                                startPos.append((int(x), int(y), staffCount))
                            elif 'repeat_1' in prim:
                                (primType, x, y) = prim.strip().split(',')
                                OnePos.append((int(x), int(y), staffCount))
                            elif 'repeat_2' in prim:
                                (primType, x, y) = prim.strip().split(',')
                                TwoPos.append((int(x), int(y), staffCount))
                            else:
                                notePos.append(noteStaffPos)
                                noteStaffPos = []
                                staffCount += 1

                        for starts in startPos:
                            (x, y, staffCount) = starts
                            beforesR = list(filter(lambda note: note[0] < x, notePos[staffCount]))
                            beforesL = list(filter(lambda note: note[0] < x, notePos[staffCount+1]))
                            befores = beforesL + beforesR
                            if('page' not in outputDict or len(outputDict['page']) == 0):
                                startCount = len(befores)
                            else:
                                startCount = len(befores) + outputDict['page'][-1]
                            if('start' in outputDict):
                                outputDict['start'].append(startCount)
                            else:
                                outputDict['start'] = [startCount]
                        print(noteCount)
            print(outputDict)
            with open(outputFolder+filename+'.json', 'w') as fp:
                json.dump(outputDict, fp)

def main():
    rootPath = '../../static/scores'
    outputPath = '../../static/images'
    inputPath = '../../static/input'

    # Get scores from database
    files = getTargetFile(rootPath)
    print('Got pdf scores from database')
    
    # # Convert the scores from database to images and return path to that image folder
    # imagesPath = []
    # for file in files:
    #     imagesPath.append(convertPdfToImage(file, outputPath))
    # print('pdf scores converted to jpeg files')

    
    # # Get the input image
    # inputImg = getInputImg(inputPath)
    # print(inputImg + ' get from input folder')

    # # Get the title text
    # title = getTitle(inputImg)
    # cur = time.time()
    # # Get the database titles
    # dbTitles = getDBTitles(rootPath)

    # # Get the database title that matches the most
    # scoreTitle = matchTitle(title, dbTitles)
    # print(scoreTitle)
    # end = time.time()
    # print(end-cur)

    # # Check which score in database the input matches to and return its name
    # differences = []
    # for imagePath in imagesPath:
    #     try:
    #         difference = checkDiff(inputImg, imagePath)
    #         print(imagePath, difference)
    #     except Exception as e:
    #         print(e)

    # Output flip points
    flipPoints = findFlipPoint(files);





main()