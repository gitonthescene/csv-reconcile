# [[https://en.wikipedia.org/wiki/S%C3%B8rensen%E2%80%93Dice_coefficient]]
def getDiceCoefficient(bigram1, bigram2):
    '''
    Calculate the Dice coefficient from two normalized sets of bigrams
    '''
    l1 = len(bigram1)
    l2 = len(bigram2)
    i1 = i2 = cnt = 0

    while i1 < l1 and i2 < l2:
        b1 = bigram1[i1:i1 + 2]
        b2 = bigram2[i2:i2 + 2]
        if b1 == b2:
            cnt += 1
            i1 += 2
            i2 += 2
        elif b1 < b2:
            i1 += 2
        else:
            i2 += 2

    # length is twice the number of bigrams
    return 400.0 * cnt / (l1 + l2)
