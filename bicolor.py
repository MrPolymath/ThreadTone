import sys
import cv2
import numpy as np

# Parameters
imgPath = "./einsteinSolo.png"
imgRadius = 500     # Number of pixels that the image radius is resized to

initPin = 0         # Initial pin to start threading from
nPins = 200         # Number of pins on the circular loom
nLines = 5000        # Maximal number of lines

minLoop = 3         # Disallow loops of less than minLoop lines
lineWidth = 3       # The number of pixels that represents the width of a thread
lineWeight = 15     # The weight a single thread has in terms of "darkness"

# Invert grayscale image
def invertImage(image):
    return (255-image)

# Apply circular mask to image
def maskImage(image, radius):
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1] # Creates two arrays from -radius to radius+1
    mask = x**2 + y**2 > radius**2 # Returns true for all the points outside a circe of radius = radius
    image[mask] = 0 # sets to black all points outside the circle

    return image

# Compute coordinates of loom pins
def pinCoords(radius, nPins=200, offset=0, x0=None, y0=None):
    alpha = np.linspace(0 + offset, 2*np.pi + offset, nPins + 1)

    if (x0 == None) or (y0 == None):
        x0 = radius + 1
        y0 = radius + 1

    coords = []
    for angle in alpha[0:-1]: # Loop backwards
        x = int(x0 + radius*np.cos(angle))
        y = int(y0 + radius*np.sin(angle))

        coords.append((x, y))
    return coords

# Compute a line mask
def linePixels(pin0, pin1):
    # Calculate the length of the line in pixels with the hypothenusa
    length = int(np.hypot(pin1[0] - pin0[0], pin1[1] - pin0[1]))

    x = np.linspace(pin0[0], pin1[0], length) # Create an array of X coords and the calculated length from the starting point to the new point
    y = np.linspace(pin0[1], pin1[1], length) # Create an array of Y coords and the calculated length from the starting point to the new point

    # Return the arrays of coords with only int values
    return (x.astype(np.int)-1, y.astype(np.int)-1)


if __name__=="__main__":

    # Load image
    image = cv2.imread(imgPath)

    print "[+] loaded " + imgPath + " for threading.."

    # Crop image
    # get the size of the image
    height, width = image.shape[0:2] # image.shape[0] is the height, [1] is the width
    # find the smallest dimension
    minEdge= min(height, width)
    # set the top and left edges
    topEdge = int((height - minEdge)/2)
    leftEdge = int((width - minEdge)/2)
    # crop the image by selecting a part of the original image and rewriting on it
    imgCropped = image[topEdge:topEdge+minEdge, leftEdge:leftEdge+minEdge]
    # save the cropped image
    cv2.imwrite('./cropped.png', imgCropped)

    # Convert to grayscale
    imgGray = cv2.cvtColor(imgCropped, cv2.COLOR_BGR2GRAY)
    # Save the grayscale image
    cv2.imwrite('./gray.png', imgGray)

    # Resize image
    imgSized = cv2.resize(imgGray, (2*imgRadius + 1, 2*imgRadius + 1))

    # Invert image colors
    imgInverted = invertImage(imgSized)
    cv2.imwrite('./inverted.png', imgInverted) # save inverted image

    # Mask image (apply a circular mask)
    imgMasked = maskImage(imgInverted, imgRadius)
    cv2.imwrite('./masked.png', imgMasked) # save masked image

    # Mask another image for white colors
    imgMaskedW = maskImage(imgInverted, imgRadius)
    cv2.imwrite('./maskedW.png', imgMaskedW) # save masked image

    # cv2.imshow('imageMasked', imgMasked)
    print "[+] image preprocessed for threading.."

    # Define pin coordinates
    coords = pinCoords(imgRadius, nPins) # returns an array of tuples with (x, y) values
    height, width = imgMasked.shape[0:2]

    # image result is rendered to
    imgResult = 255 * np.ones((height, width)) # create array of 255 (white color) with the size of the resulting image

    # Initialize variables
    i = 0
    lines = []
    previousPins = []
    oldPin = initPin
    lineMask = np.zeros((height, width))

    # do I need this?
    # imgResult = 255 * np.ones((height, width))

    # Loop over lines until stopping criteria is reached
    for line in range(nLines):
        i += 1
        bestLine = 0
        oldCoord = coords[oldPin]
        color = 0 # We start calculating best lines for black color

        # Loop over possible lines
        for index in range(1, nPins):
            pin = (oldPin + index) % nPins # get pin position

            coord = coords[pin] # get coordinates of the pin

            xLine, yLine = linePixels(oldCoord, coord) # return two array of coordinates

            # Fitness function
            lineSum = np.sum(imgMasked[yLine, xLine]) # get the rgb values (only one value because its B&W) and add them together
            # The bigger the value, the darker the line, beacause the colors are inverted

            # Find the best sum and set it as the best line if the pin wasnt used recently (defined by minLoop)
            if (color == 0) and (lineSum > bestLine) and not(pin in previousPins):
                bestLine = lineSum
                bestPin = pin
            if (color == 1) and (lineSum < bestLine) and not(pin in previousPins):
                bestLine = lineSum
                bestPin = pin

        # Update previous pins
        # if there is more previousPins than the minLoop, extract the first one from the array
        if len(previousPins) >= minLoop:
            previousPins.pop(0)
        # Add bestPin to the array of previousPins
        previousPins.append(bestPin)

        # Subtract new line from image
        if color == 0:
            lineMask = lineMask * 0
        if color == 1:
            lineMask = lineMask * 0 + 255

        # lineWeight es en realitat un color de 0 a 255 (15 es un color molt fosc)
        cv2.line(lineMask, oldCoord, coords[bestPin], lineWeight, lineWidth)
        # Substract from the inverted image the lineWeight along the line
        # Because dark colors are light (inverted image), substracting 15 (dark color)

        imgMasked = np.subtract(imgMasked, lineMask)
        # cv2.imshow('imageMasked', imgMasked)
        # Save line to results
        lines.append((oldPin, bestPin))

        # plot results
        xLine, yLine = linePixels(coords[bestPin], coord)
        imgResult[yLine, xLine] = 0
        cv2.imshow('image', imgResult)
        cv2.waitKey(1)

        # Break if no lines possible
        if bestPin == oldPin:
            if color == 1:
                break
            color = 1 # Set color to 1 to start white
            print "Black lines computed. Starting white lines"

        # Prepare for next loop
        oldPin = bestPin

        # Print progress
        sys.stdout.write("\b\b")
        sys.stdout.write("\r")
        sys.stdout.write("[+] Computing line " + str(line + 1) + " of " + str(nLines) + " total")
        sys.stdout.flush()

    print "\n[+] Image threaded"

    # Wait for user and save before exit
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    cv2.imwrite('./threaded.png', imgResult)
    cv2.imwrite('./processed.png', imgMasked)

    svg_output = open('threaded.svg','wb')
    header="""<?xml version="1.0" standalone="no"?>
    <svg width="%i" height="%i" version="1.1" xmlns="http://www.w3.org/2000/svg">
    """ % (width, height)
    footer="</svg>"
    svg_output.write(header)
    pather = lambda d : '<path d="%s" stroke="black" stroke-width="0.5" fill="none" />\n' % d
    pathstrings=[]
    pathstrings.append("M" + "%i %i" % coords[lines[0][0]] + " ")
    for l in lines:
        nn = coords[l[1]]
        pathstrings.append("L" + "%i %i" % nn + " ")
    pathstrings.append("Z")
    d = "".join(pathstrings)
    svg_output.write(pather(d))
    svg_output.write(footer)
    svg_output.close()

    csv_output = open('threaded.csv','wb')
    csv_output.write("x1,y1,x2,y2\n")
    csver = lambda c1,c2 : "%i,%i" % c1 + "," + "%i,%i" % c2 + "\n"
    for l in lines:
        csv_output.write(csver(coords[l[0]],coords[l[1]]))
    csv_output.close()
