import os
from datetime import datetime

ext2File = open('agwc.txt', 'rb')
ext2 = list(ext2File.read())

def toInt(x):
    return int.from_bytes(bytes(x), 'little')

# -------------------------------------------------------------------------------
# ------- Superblock
# -------------------------------------------------------------------------------
sb = ext2[1024:2048]

inodes = sb[0:4]
blocks = sb[4:8]
superuser_blocks = sb[8:12]
magic_number = sb[56:58]
last_mount = sb[44:48]
fragment_size = sb[28:32]
blocks_in_group = sb[32:36]

block_size = 1024 << toInt(sb[24:28])
# print(hex(toInt(magic_number)))
# print(block_size)
# -------------------------------------------------------------------------------
# ------- Block group descriptor
# -------------------------------------------------------------------------------
def getBlock(block):
    return ext2[(block*block_size):(block*block_size+block_size)]

bgd = getBlock(1)

# -------------------------------------------------------------------------------
# ------- Inode table
# -------------------------------------------------------------------------------
inode_table = getBlock(toInt(bgd[8:12]))

# -------------------------------------------------------------------------------
# ------- Inodes
# -------------------------------------------------------------------------------
def getInode(inode):
    return inode_table[(inode*128):(inode*128+128)]

def getInodeDataPointers(inode):
    pointers = []
    i = 40
    while(i < 88):
        pointers.append(toInt(inode[i:i+4]))
        i += 4
    return pointers

def getInodeInfo(inode):
    print('Type/Permission', hex(toInt(inode[0:2])))
    ts = toInt(inode[8:12])
    print('Last Access Time', datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))
    print('Data pointers')
    i = 40
    while i < 88:
        print('\t', toInt(inode[i:i+4]))
        i += 4
    print('Singly:', toInt(inode[88:92]))
    print('Doubly:', toInt(inode[92:96]))
    print('Triply:', toInt(inode[96:100]))
    print()

# print('Reserved inodes')
# for i in range(10):
#     inode = getInode(i)
#     print(i + 1, end=' ')
#     getInodeInfo(inode)

# first_inode = 10
# print('Inodes')
# for i in range(5):
#     inode = getInode(first_inode + i)
#     print(first_inode + i + 1, end=' ')
#     getInodeInfo(inode)

# for i in range(128):
#     inode_2 = getInode(i)

#     last_file_access = toInt(inode_2[8:12])
#     number_of_data_blocks = toInt(inode_2[32:36])
#     file_size = toInt(inode_2[4:8])

#     # print(toInt(bgd[16:18]))
#     print(i, file_size)

# quit()

# for i, x in enumerate(inode):
#     print(i, x)
# print(inode)
# print(toInt(inode[40:44]))
# print(toInt(inode[48:52]))
# print(getBlock(137))
# quit()

def getDataPointersFromIndirectPointer(block, level):
    pointers = []
    block = getBlock(block)
    i = 0
    while(i < block_size):
        pointer = toInt(block[i:i+4])
        if pointer == 0:
            break
        pointers.append(pointer)
        i += 4

    if level == 1:
        return pointers

    allPointers = []
    for p in pointers:
        allPointers += getDataPointersFromIndirectPointer(p, level - 1)
    return allPointers

def trimZerosAtEnd(data):
    index = len(data)
    for i, d in enumerate(reversed(data)):
        if d != 0:
            index -= i
            break
    return data[:index]

def saveFile(inode, fileName):
    pointers = getInodeDataPointers(inode)
    singly = toInt(inode[88:92])
    doubly = toInt(inode[92:96])
    triply = toInt(inode[96:100])
    if singly != 0:
        pointers += getDataPointersFromIndirectPointer(singly, 1)
    if doubly != 0:
        pointers += getDataPointersFromIndirectPointer(doubly, 2)
    if triply != 0:
        pointers += getDataPointersFromIndirectPointer(triply, 3)

    data = []
    for pointer in pointers:
        if pointer == 0:
            continue
        data += getBlock(pointer)
    data = trimZerosAtEnd(data)

    bytes = bytearray(data)
    newFile = open(fileName, 'wb')
    newFile.write(bytes)

def getDirectoryInfo(inode):
    directory = []
    pointers = getInodeDataPointers(inode)
    block = getBlock(pointers[0])
    b = 0
    while True:
        entry = {}
        entryBytes = block[b:]

        entry['inode_number'] = toInt(entryBytes[0:4])
        if entry['inode_number'] == 0:
            return directory

        entry['rec_length'] = toInt(entryBytes[4:6])
        entry['name_length'] = toInt(entryBytes[6:7])
        entry['file_type'] = toInt(entryBytes[7:8])

        chars = []
        for i in range(entry['name_length']):
            chars.append(chr(entryBytes[8+i:8+i+1][0]))
        entry['name'] = ''.join(chars)

        b += entry['rec_length']
        directory.append(entry)

def printDirectoryInfo(inode):
    directory = getDirectoryInfo(inode)
    for entry in directory:
        print('Inode number:\t', entry['inode_number'])
        print('Rec length:\t', entry['rec_length'])
        print('Name length:\t', entry['name_length'])
        print('File type:\t', entry['file_type'])
        print('Name:\t\t', entry['name'])
        print()

# Manual
# printDirectoryInfo(getInode(14 - 1))
# saveFile(getInode(12 - 1), 'agwc.jpg')

# Automatic
root = getDirectoryInfo(getInode(2 - 1))
try:
    os.mkdir('root')
except Exception as e:
    quit(e)
os.chdir('root')

def createFolderStructure(directory):
    for entry in directory:
        if entry['file_type'] == 2 and entry['name'] != '.' and entry['name'] != '..':
            os.mkdir(entry['name'])
            currDir = os.getcwd()
            os.chdir(entry['name'])
            createFolderStructure(getDirectoryInfo(getInode(entry['inode_number'] - 1)))
            os.chdir(currDir)
        elif entry['file_type'] == 1:
            saveFile(getInode(entry['inode_number'] - 1), entry['name'])

createFolderStructure(root)
