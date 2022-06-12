import os
import exifread
import shutil
import grp, pwd, time
import xml.dom.minidom
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
# from pyexiv2 import Image
from PIL import Image
from PIL.PngImagePlugin import PngImageFile


#要迁移的照片，${synology_user_name}为synology的用户名
scanPath = "/var/services/homes/${synology_user_name}/photo"
#迁移照片的目的地，${synology_user_name}为synology的用户名
toPath = "/var/services/homes/${synology_user_name}/Photos/PhotoLibrary/"

def syncFilePath(file):
    global toPath

    if not os.path.exists(file):
        print(file, "文件不存在")
        return 0

    filePath, fileName = os.path.split(file)

    #获取新文件的地址及文件名
    fileSuffix = os.path.splitext(fileName)[-1][1:].lower()
    if fileSuffix in ('jpeg', 'jpg', 'heic'):
        f = open(file, "rb")
        tags = exifread.process_file(f)
        dateKey = 'EXIF DateTimeOriginal'

        #过滤没有拍摄时间的照片
        if dateKey not in tags:
            return 0

        dateTimeOriginal = tags[dateKey].values

        toNewFile = os.path.join(toPath, dateTimeOriginal[0:4], dateTimeOriginal[5:7], fileName)
    elif fileSuffix in ('mp4', 'mov'):
        #取媒体拍摄时间
        metadata = extractMetadata(createParser(file))
        metaCreateDate = metadata.get('creation_date')
        toNewFile = os.path.join(toPath, str(metaCreateDate.year), str(metaCreateDate.month).zfill(2), fileName)
    elif fileSuffix in ('png'):
        im = Image.open(file)
        xmlDom = xml.dom.minidom.parseString(im.info.get("XML:com.adobe.xmp"))
        root = xmlDom.documentElement
        dateCreatedElement = root.getElementsByTagName('photoshop:DateCreated')
        pngCreateDate = dateCreatedElement[0].firstChild.data
        toNewFile = os.path.join(toPath, pngCreateDate[0:4], pngCreateDate[5:7], fileName)
    else:
        print(file, "该文件类型不能处理，跳过")
        return 0

    #如果变更后的文件地址跟现在一样，那就不处理
    if file == toNewFile:
        return 0

    toNewFilePath = os.path.split(toNewFile)[0]
    if not os.path.exists(toNewFilePath):
        #如果目的地目录不存在，则创建目录，user和group信息用源照片的user和group信息
        userName = os.popen("ls -al "+file+" |awk '{print $3}'").read().strip()
        groupName = os.popen("ls -al "+file+" |awk '{print $4}'").read().strip()
        uid = pwd.getpwnam(userName).pw_uid
        gid = grp.getgrnam(groupName).gr_gid
        os.makedirs(toNewFilePath)
        os.chown(toNewFilePath, uid, gid)

    shutil.move(file, toNewFile)
    print(file, toNewFile)
    #如果源目录是群晖的相册目录，删除用于全局搜索的系统文件
    eaDir = os.path.join(filePath, "@eaDir", fileName)
    if os.path.exists(eaDir):
        shutil.rmtree(eaDir)
    return 1

def scan():
    global scanPath

    g = os.walk(scanPath)
    for path,dirList,fileList in g:
        
        for fileName in fileList:
            #过滤群晖用于全局搜索的系统文件
            if "@eaDir" in fileName or "@eaDir" in path:
                continue

            file = os.path.join(path, fileName)
            result = syncFilePath(file)

def getxmp(self):
    for segment, content in self.applist:
        if segment == 'APP1':
            marker, xmp_tags = content.rsplit(b'\x00', 1)
            if marker == b'http://ns.adobe.com/xap/1.0/':
                root = xml.etree.ElementTree.fromstring(xmp_tags)
    return root
#同步指定目录的照片及视频
# scan()

#用于单个文件测试
#syncFilePath("/var/services/homes/${synology_user_name}/xxx.jpg")