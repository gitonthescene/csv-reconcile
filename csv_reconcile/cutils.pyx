from libc.string cimport strncmp
# [[https://en.wikipedia.org/wiki/S%C3%B8rensen%E2%80%93Dice_coefficient]]
# Could speed this up using Cython
def getDiceCoefficient(const char* bigram1, const char* bigram2):
    '''
    Calculate the Dice coefficient from two normalized sets of bigrams
    '''
    cdef int l1, l2, i1, i2, cnt, diff
    l1 = len(bigram1)
    l2 = len(bigram2)
    i1 = i2 = cnt = 0

    while i1 < l1 and i2 < l2:
        diff = strncmp( bigram1+i1, bigram2+i2, 2)
        if diff == 0:
            cnt += 1
            i1 += 2
            i2 += 2
        elif diff < 0:
            i1 += 2
        else:
            i2 += 2

    # length is twice the number of bigrams
    return 400.0 * cnt / (l1 + l2)
