#from __future__ import print_function
import json
import os
import tangelo
from PIL import ImageFilter, Image
import base64
import cStringIO
import sys


@tangelo.restful
def post(mediafile=None,targetHeight=512,*args,**kwargs):
    # get the protocol versio

    dataset_path = os.environ.get('TRAINING_DATA_ROOT')
    media_file_path = dataset_path+'/media/'+mediafile
    print 'reading media file:',media_file_path
    sys.stdout.flush()

    #try:
    with open(media_file_path) as f:
        im = Image.open(f)

        width = im.width
        height = im.height

        factor = float(targetHeight)/float(im.height)
        print('factor:',factor)
        newH = int(im.height*factor)
        newW = int(im.width*factor)
        im.resize((newW,newH))
        print 'new width:',newW, 'new height:',newH

        buffer = cStringIO.StringIO()
        im.save(buffer, format="JPEG")
        img_str = base64.b64encode(buffer.getvalue())

        return img_str
    #except: 
    #    return {'status':'failure','mediafile':mediafile}