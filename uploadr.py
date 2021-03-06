#!/usr/bin/env python

import sys, time, os, urllib2, shelve, string, xmltramp, mimetools, mimetypes, md5, webbrowser, unicodedata
#
#   uploadr.py
#
#   Upload images placed within a directory to your Flickr account.
#
#   Requires:
#       xmltramp http://www.aaronsw.com/2002/xmltramp/
#       flickr account http://flickr.com
#
#   Inspired by:
#        http://micampe.it/things/flickruploadr
#        Cameron Mallory   cmallory/berserk.org
#
#   Usage:
#
#   The best way to use this is to just fire this up in the background and forget about it.
#   If you find you have CPU/Process limits, then setup a cron job.
#
#   %nohup python uploadr.py  -d &
#
#   cron entry (runs at the top of every hour )
#   0  *  *   *   * /full/path/to/uploadr.py > /dev/null 2>&1
#
#   This code has been updated to use the new Auth API from flickr.
#
#   You may use this code however you see fit in any form whatsoever.
#

##
##  Items you will want to change
## 

#
# Location to scan for new images
#   
IMAGE_DIR = "/media/disk/pictures/"  

#
# Locations to ignore
#
EXCLUDED_DIRS = [".picasaoriginals"] 

#
#   Flickr settings
#
FLICKR = {"title": "",
        "description": "",
        "tags": "uploader",
        "is_public": "0",
        "is_friend": "0",
        "is_family": "1" }
#
#   How often to check for new images to upload  (in seconds )
#
SLEEP_TIME = 10 * 60

##
##  You shouldn't need to modify anything below here
##
FLICKR["secret" ] = "fb2377b77bd2639c"
FLICKR["api_key" ] = "2d7076217eb2dc94997cba1bb61bd5b5"
class APIConstants:
    base = "https://flickr.com/services/"
    rest   = base + "rest/"
    auth   = base + "auth/"
    upload = base + "upload/"
    
    token = "auth_token"
    secret = "secret"
    key = "api_key"
    sig = "api_sig"
    frob = "frob"
    perms = "perms"
    method = "method"
    
    def __init__( self ):
       pass
       
api = APIConstants()

class Uploadr:
    token = None
    perms = ""
    TOKEN_FILE = ".flickrToken"
    listings = {}
    
    def __init__( self ):
        self.token = self.getCachedToken()



    """
    Signs args via md5 per http://www.flickr.com/services/api/auth.spec.html (Section 8)
    """
    def signCall( self, data):
        keys = data.keys()
        keys.sort()
        foo = ""
        for a in keys:
            foo += (a + data[a])
        
        f = FLICKR[ api.secret ] + api.key + FLICKR[ api.key ] + foo
        #f = api.key + FLICKR[ api.key ] + foo
        return md5.new( f ).hexdigest()
   
    def urlGen( self , base,data, sig ):
        foo = base + "?"
        for d in data: 
            foo += d + "=" + data[d] + "&"
        return foo + api.key + "=" + FLICKR[ api.key ] + "&" + api.sig + "=" + sig
        
 
    #
    #   Authenticate user so we can upload images
    #
    def authenticate( self ):
        print "Getting new Token"
        self.getFrob()
        self.getAuthKey()
        self.getToken()   
        self.cacheToken()

    """
    flickr.auth.getFrob
    
    Returns a frob to be used during authentication. This method call must be 
    signed.
    
    This method does not require authentication.
    Arguments
    
    api.key (Required)
    Your API application key. See here for more details.     
    """
    def getFrob( self ):
        d = { 
            api.method  : "flickr.auth.getFrob"
            }
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        try:
            response = self.getResponse( url )
            if ( self.isGood( response ) ):
                FLICKR[ api.frob ] = str(response.frob)
            else:
                self.reportError( response )
        except:
            print "Error getting frob:" , str( sys.exc_info() )

    """
    Checks to see if the user has authenticated this application
    """
    def getAuthKey( self ): 
        d =  {
            api.frob : FLICKR[ api.frob ], 
            api.perms : "write"  
            }
        sig = self.signCall( d )
        url = self.urlGen( api.auth, d, sig )
        ans = ""
        try:
            webbrowser.open( url )
            ans = raw_input("Have you authenticated this application? (Y/N): ")
        except:
            print str(sys.exc_info())
        if ( ans.lower() == "n" ):
            print "You need to allow this program to access your Flickr site."
            print "A web browser should pop open with instructions."
            print "After you have allowed access restart uploadr.py"
            sys.exit()    

    """
    http://www.flickr.com/services/api/flickr.auth.getToken.html
    
    flickr.auth.getToken
    
    Returns the auth token for the given frob, if one has been attached. This method call must be signed.
    Authentication
    
    This method does not require authentication.
    Arguments
    
    NTC: We need to store the token in a file so we can get it and then check it insted of
    getting a new on all the time.
        
    api.key (Required)
       Your API application key. See here for more details.
    frob (Required)
       The frob to check.         
    """   
    def getToken( self ):
        d = {
            api.method : "flickr.auth.getToken",
            api.frob : str(FLICKR[ api.frob ])
        }
        sig = self.signCall( d )
        url = self.urlGen( api.rest, d, sig )
        try:
            res = self.getResponse( url )
            if ( self.isGood( res ) ):
                self.token = str(res.auth.token)
                self.perms = str(res.auth.perms)
                self.cacheToken()
            else :
                self.reportError( res )
        except:
            print str( sys.exc_info() )

    """
    Attempts to get the flickr token from disk.
    """
    def getCachedToken( self ): 
        if ( os.path.exists( self.TOKEN_FILE )):
            return open( self.TOKEN_FILE ).read()
        else :
            return None
        


    def cacheToken( self ):
        try:
            open( self.TOKEN_FILE , "w").write( str(self.token) )
        except:
            print "Issue writing token to local cache " , str(sys.exc_info())



    """
    Attempts to get the flickr token from disk.
    """
    def getCachedPhotoSetId( self, photoSetIdFile): 
        if ( os.path.exists( photoSetIdFile )):
            return open( photoSetIdFile ).read()
        else :
            return None

    """
    Store photoSetId on local file
    """
    def setCachedPhotoSetId( self, photoSetIdFile, photoSetId ):
        try:
            open( photoSetIdFile , "w").write( str(photoSetId) )
        except:
            print "Issue writing photoSetId to local photoSetIdFile " , str(sys.exc_info())



    """
    flickr.auth.checkToken

    Returns the credentials attached to an authentication token.
    Authentication
    
    This method does not require authentication.
    Arguments
    
    api.key (Required)
        Your API application key. See here for more details.
    auth_token (Required)
        The authentication token to check. 
    """
    def checkToken( self ):    
        if ( self.token == None ):
            return False
        else :
            d = {
                api.token  :  str(self.token) ,
                api.method :  "flickr.auth.checkToken"
            }
            sig = self.signCall( d )
            url = self.urlGen( api.rest, d, sig )     
            try:
                res = self.getResponse( url ) 
                if ( self.isGood( res ) ):
                    self.token = res.auth.token
                    self.perms = res.auth.perms
                    return True
                else :
                    self.reportError( res )
            except:
                print str( sys.exc_info() )          
            return False
     
             
    def upload( self ):
        print "Starting upload"
        newImages = self.grabNewImages()
        if ( not self.checkToken() ):
            self.authenticate()
        for image in newImages:
            self.uploadImage( image )
        print "End of upload"
        sys.stdout.flush()
        
    def grabNewImages( self ):
        images = []
        foo = os.walk( IMAGE_DIR )
        for data in foo:
            (dirpath, dirnames, filenames) = data
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
            #print "Scanning", dirpath
            for f in filenames :
                ext = f.lower().split(".")[-1]
                if ( ext == "jpg" or ext == "jpeg" or ext == "raw" or ext == "gif" or ext == "png" or ext == "mov" or ext == "mpeg" or ext == "wmv" or ext == "avi" ):
                    images.append( os.path.normpath( dirpath + "/" + f ) )
        images.sort()
        print str(len(images)) + " images listed. Wait while checking uploads (this may be very long)..."
        sys.stdout.flush()
        return images
                   
    
    def uploadImage( self, image ):
        if ( not self.isAlreadyUploaded(image) ):
            print "Uploading ", image , "...",
            try:
                photo = ('photo', image, open(image,'rb').read())
                filename = self.getImageTitle(image)
                d = {
                    api.token   : str(self.token),
                    api.perms   : str(self.perms),
                    "tags"      : str( FLICKR["tags"] ),
                    "is_public" : str( FLICKR["is_public"] ),
                    "is_friend" : str( FLICKR["is_friend"] ),
                    "is_family" : str( FLICKR["is_family"] ),
                    "title"     : str( filename )
                }
                sig = self.signCall( d )
                d[ api.sig ] = sig
                d[ api.key ] = FLICKR[ api.key ]        
                url = self.build_request(api.upload, d, (photo,))    
                xml = urllib2.urlopen( url ).read()
                res = xmltramp.parse(xml)
                if ( self.isGood( res ) ):
                    print "successful."
                    self.addImageToFlickrSet( res.photoid, image )
                else :
                    print "problem.."
                    self.reportError( res )
                sys.stdout.flush()
            except:
                print str(sys.exc_info())
        else:
            #print "Already uploaded image", image
            pass

    """
    get Image title from image file
    """
    def getImageTitle(self, image):
        filename = os.path.splitext(os.path.basename(image))[0]
        nkfd_form = unicodedata.normalize('NFKD', unicode(filename, errors='ignore'))
        ufilename = u"".join([c for c in nkfd_form if not unicodedata.combining(c)])
        return ufilename.encode('ascii', 'ignore')

    """
    Get photos listing from a file
    """
    def isAlreadyUploaded(self, image ):
        photoSetIdFile = os.path.normpath( os.path.dirname(image) + "/" + ".flickrPhotoSetId" )
        photoSetId = self.getCachedPhotoSetId( photoSetIdFile )
        filename = self.getImageTitle(image)
        if photoSetId != None:
            if photoSetId not in self.listings:
                self.getPhotoListingFromPhotoSet(photoSetId)
            if photoSetId in self.listings:
                return filename in self.listings[photoSetId]
        return False


    """
    """
    def addImageToFlickrSet( self, photoId, image ):
        directoryName = image.lower().split("/")[-2]
        photoSetIdFile = os.path.normpath( os.path.dirname(image) + "/" + ".flickrPhotoSetId" )
        photoSetId = self.getCachedPhotoSetId( photoSetIdFile )
        if photoSetId == None:
            self.createPhotoSet(photoSetIdFile, directoryName, photoId)
        else :
            self.addPhotoToPhotoSet( photoSetIdFile, directoryName, photoId,photoSetId)

    """
    Create a new PhotoSet
    """
    def createPhotoSet( self, photoSetIdFile, directoryName, photoId):
        print "Creating photoSet for folder", directoryName , "...",
        d = {
            api.method   : "flickr.photosets.create",
            api.token    : str(self.token),
            api.perms    : str(self.perms),
            "title"      : str(directoryName),
            "description": str(directoryName),
            "primary_photo_id"   : str(photoId)
        }
        sig = self.signCall( d )
        d[ api.sig ] = sig
        d[ api.key ] = FLICKR[ api.key ]        
        url = self.build_request(api.rest, d, ())    
        xml = urllib2.urlopen( url ).read()
        res = xmltramp.parse(xml)
        if ( self.isGood( res ) ):
            print "successful."
            photoSetId  = res.photoset('id')
            self.listings[photoSetId] = [];
            self.setCachedPhotoSetId(photoSetIdFile, photoSetId)
        else :
            print "problem.."
            self.reportError( res )
        sys.stdout.flush()



    """
    Add a photo to an existing photoSet
    """
    def addPhotoToPhotoSet( self, photoSetIdFile, directoryName, photoId, photoSetId):
        #print "Addind photo to existing photoSet",photoSetId,"...",
        d = {
            api.method   : "flickr.photosets.addPhoto",
            api.token    : str(self.token),
            api.perms    : str(self.perms),
            "photoset_id": str( photoSetId ),
            "photo_id"   : str( photoId )
        }
        sig = self.signCall( d )
        d[ api.sig ] = sig
        d[ api.key ] = FLICKR[ api.key ]        
        url = self.build_request(api.rest, d, ())    
        xml = urllib2.urlopen( url ).read()
        res = xmltramp.parse(xml)
        if ( self.isGood( res ) ):
            #print "successful."
            pass
        else :
            print "Addind photo to existing photoSet",photoSetId,"...","problem.."
            self.reportError( res )
            self.createPhotoSet(photoSetIdFile, directoryName, photoId)
        sys.stdout.flush()


    """
    Get photoSet photos listing
    """
    def getPhotoListingFromPhotoSet( self, photoSetId, page=1):
        #print "Getting photo listing for photoset", photoSetId, "for page", page, "...",
        d = {
            api.method   : "flickr.photosets.getPhotos",
            api.token    : str(self.token),
            api.perms    : str(self.perms),
            "photoset_id": str( photoSetId ),
            "per_page"   : str( 500 ),
            "page"       : str( page )
        }
        sig = self.signCall( d )
        d[ api.sig ] = sig
        d[ api.key ] = FLICKR[ api.key ]
        url = self.build_request(api.rest, d, ())
        xml = urllib2.urlopen( url ).read()
        res = xmltramp.parse(xml)
        if ( self.isGood( res ) ):
            #print "successful."
            photos = []
            for photo in res.photoset:
                photos.append(photo('title').encode('ascii', 'ignore'))
            if photoSetId in self.listings :
                self.listings[photoSetId].extend(photos)
            else :
                self.listings[photoSetId] = photos
            if int(res.photoset('page')) < int(res.photoset('pages')) :
                self.getPhotoListingFromPhotoSet(photoSetId, page+1)
        else :
            print "Problem while getting photo listing for photoset",photoSetId
            self.reportError( res )
        sys.stdout.flush()

    #
    #
    # build_request/encode_multipart_formdata code is from www.voidspace.org.uk/atlantibots/pythonutils.html
    #
    #
    def build_request(self, theurl, fields, files, txheaders=None):
        """
        Given the fields to set and the files to encode it returns a fully formed urllib2.Request object.
        You can optionally pass in additional headers to encode into the opject. (Content-type and Content-length will be overridden if they are set).
        fields is a sequence of (name, value) elements for regular form fields - or a dictionary.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files.    
        """
        content_type, body = self.encode_multipart_formdata(fields, files)
        if not txheaders: txheaders = {}
        txheaders['Content-type'] = content_type
        txheaders['Content-length'] = str(len(body))

        return urllib2.Request(theurl, body, txheaders)     

    def encode_multipart_formdata(self,fields, files, BOUNDARY = '-----'+mimetools.choose_boundary()+'-----'):
        """ Encodes fields and files for uploading.
        fields is a sequence of (name, value) elements for regular form fields - or a dictionary.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files.
        Return (content_type, body) ready for urllib2.Request instance
        You can optionally pass in a boundary string to use or we'll let mimetools provide one.
        """    
        CRLF = '\r\n'
        L = []
        if isinstance(fields, dict):
            fields = fields.items()
        for (key, value) in fields:   
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            filetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % filetype)
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY        # XXX what if no files are encoded
        return content_type, body
    
    
    def isGood( self, res ):
        if ( not res == "" and res('stat') == "ok" ):
            return True
        else :
            return False
            
            
    def reportError( self, res ):
        try:
            print "Error:", str( res.err('code') + " " + res.err('msg') )
        except:
            print "Error: " + str( res )
        sys.stdout.flush()

    """
    Send the url and get a response.  Let errors float up
    """
    def getResponse( self, url ):
        xml = urllib2.urlopen( url ).read()
        return xmltramp.parse( xml )
            

    def run( self ):
        while ( True ):
            self.upload()
            print "Last check: " , str( time.asctime(time.localtime()))
            sys.stdout.flush()
            time.sleep( SLEEP_TIME )
      
if __name__ == "__main__":
    flick = Uploadr()
    
    if ( len(sys.argv) >= 2  and sys.argv[1] == "-d"):
        flick.run()
    else:
        flick.upload()
