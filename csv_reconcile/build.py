import os.path


def dummydoc():
    if not os.path.exists("README.md"):
        print("Creating README.md ...")
        f = open("README.md", "w")
        f.close()
