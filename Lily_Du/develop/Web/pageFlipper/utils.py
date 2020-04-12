def _readTitle(inputImg):
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
    # cv2.imwrite('contours.png', copy)

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
    # show the output images
    # cv2.imwrite("Image.png", image)
    # cv2.imwrite("Output.png", gray)
    return text


def _getDBTitles():
    L = []
    for name in os.listdir(settings.MEDIA_ROOT):
        if os.path.isdir(os.path.join(settings.MEDIA_ROOT, name)):
            L.append(name)
    return L


def _matchTitle(inputTitle, L):
    maxRatio = 0
    scoreTitle = None
    for title in L:
        ratio = fuzz.partial_ratio(inputTitle, title)
        if(ratio > maxRatio):
            maxRatio = ratio
            scoreTitle = title
    return scoreTitle


def _getTitle():
    mediaFolder = "images"
    for filename in os.listdir(settings.MEDIA_ROOT):
        if (filename.endswith('.png') and not 'default' in filename):
            img_path = os.path.join(settings.MEDIA_ROOT, filename)
    img_title = _readTitle(img_path)
    print('Recognized title: ' + img_title)

    db_titles = _getDBTitles()
    print('Database titles: ', db_titles)

    score_title = _matchTitle(img_title, db_titles)
    print('Most closely resembled title in database: ' + score_title)

    for filename in os.listdir(settings.MEDIA_ROOT):
        if (filename.endswith('.png') and not 'default' in filename):
            os.remove(os.path.join(settings.MEDIA_ROOT, filename))

    return score_title