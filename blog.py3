# To do
# 1. Feb 22 2017 Migrate to keyring. Look at the stackoverflow post where the guy who migrated gnomekeyring to python2 now just uses the keyring package. It should be in my stackoverflow mailbox.
# 1. make a function to extract all the tags, and ignore categories. Or better yet, just ignore all tags and categories for now.
#   2. I could implement a passphrase less key for less secure things in the roots keyring. So the function blog_init, etc should take arguments that I can reuse when I call a script with my own script. It can extract metadata directly from the file, I suppose, just like this thing. All this seems so cumbersome.
# python blog_sendpage.py "filename" "

# -*- coding: utf-8 -*-
import urllib , urllib3 
import vim , xml.dom.minidom , xmlrpc , sys , string , re
# modules for me
import os, traceback, socket
#timeout socket lets me time out buggy xmlrpc calls.
import gnomekeyring as gk
# must migrate to the keyring package and support multiple keyring types.

#####################
#      Settings     #
#####################

enable_tags = 1
enable_gnome_keyring = True
# if you do not enable keyring, set the variables below
blog_username = ''
blog_password = ''
blog_url = ''
localtempdir = '/tmp'

socket.setdefaulttimeout(10) #set global timeout in 10 secs. could replace with local timeout, but what the hell

# default keyring. must already exist.
KEYRING_NAME='login'
# application name. keyring items will be set with this application name. This is how we figure out which keyring item corresponds to this plugin.
APP_NAME='vimpress'

# use for debugging output
dbg = True

# enable toc support for markdown. needs doctoc.
enable_toc_support = 1

# set default posttype
#posttype = 'post'
posttype = 'page'
# see if called from within vim
#fromvim = True

#########################
#      Global Constants #
#########################
TOC_START_STRING = '<!-- START doctoc generated TOC please keep comment here to allow auto update -->'
# Modify according to DOCTOC tag. That is, take a md file, run doctoc on it, and see the start and end comments for the doctoc generated TOC. If doctoc is updated, its quite likely that these strings will be updated.
TOC_END_STRING ='<!-- END doctoc generated TOC please keep comment here to allow auto update -->'
META_DATA_START = '%=========== Meta ============'
META_DATA_END = '%========== Content =========='
VIMSYNTAX = 'markdown'
VIMFILETYPE = 'markdown'
DOCTOCSTRING = '*generated with [DocToc](http://doctoc.herokuapp.com/)*'

#########################
#      Global variables #
#########################
blog_login_success = False

#####################
# Do not edit below #
#####################
# this is the xmlrpc serverproxy object that's returned on authentication with the blog.
global handler

# the edit variable is to set listing mode to readonly. i think its not implemented correctly. there ought to be a vim option to set to readonly mode.

edit = 1

############################################################
# python function definitions. look at end for main loop. ##
############################################################

def blog_test():
    # function tests if the blog username, password and url combo works.
    global blog_username, blog_password, handler
    try:
        # this seems to be the fastest test of blog credentials.
        # getCategories has been replaced by getTaxonomies
        l = handler.getTerms(0, blog_username, blog_password,'category')
        # if list posts successful, return 1
        return True
    except:
        sys.stderr.write("An error has occured in blog_test\n")
        if dbg:
            traceback.print_exc(file=sys.stdout)
        return False

def blog_init():
    try:
        global blog_login_success, enable_gnome_keyring, dbg

        if not blog_login_success:
            # set login details
            if enable_gnome_keyring:
                if dbg:
                    sys.stdout.write("Running blog_set_keyring_info()\n")
                blog_set_keyring_info()
                # blog_set_keyring_info sets the handler and blog_login_success.
            else:
                # set handler using the newly gained credentials
                #handler = xmlrpclib.ServerProxy(blog_url).metaWeblog
                handler = xmlrpclib.ServerProxy(blog_url).wp
                blog_login_success = blog_test()
        
        # now blog_username, blog_password and blog_url should be set from the keyring or directly in the script.

        # check if blog_login_success
        if not blog_login_success:
            sys.stderr.write("Blog login failed\n")
            # sys.exit does not work well inside vim. it kills vim too.
            #sys.exit(1)
    except:
        sys.stderr.write("Error in blog_init().")

def blog_set_keyring_info(fromvim=True):
    # if calling from a shell, set fromvim to False
    # sees if keyring items already exist by searching for the attribute APP_NAME in KEYRING_NAME. 
    # picks the first keyring item found - who has multiple blogs. nevertheless, this is a bug.
    global blog_username, blog_password, blog_url, handler, blog_login_success

    try:
        keyrings = gk.list_keyring_names_sync()
        # if the KEYRING_NAME exists at all, continue.
        if KEYRING_NAME in keyrings:
            # search for the appname in the list of keys
            atts = {'appname':APP_NAME}
            try:
                # find keys created by the app. I'll assume the appname is unique.
                keylist = gk.find_items_sync(gk.ITEM_GENERIC_SECRET,atts)
                sys.stdout.write("Login credentials found.\n")
                found_keys = True
            except: 
                #If nothing found, gk.find_items_sync throws a NoMatchError (but I can't seem to catch the error by name)
                sys.stderr.write("No keys found\n")
                found_keys = False
            # we to try except, otherwise the find_items_sync function will throw an exception if no matches are found.
            

            if found_keys:
                # pop the first item in the search list. will fix this in the future: have to list all display names (uniquely defined) and let the user select the one that works. currently we just pick the first key as unique.
                
                acceptkey = False
                while (not acceptkey) and (len(keylist) > 0):
                    key = keylist.pop()
                    # key is an object with attributes like keyring, attributes, password and secret. It does not contain the displayname. These are not object methods.

                    #item_info = gk.item_get_info_sync(KEYRING_NAME,key.item_id)
                    blog_username = key.attributes['username']
                    blog_password = key.secret
                    blog_url = key.attributes['url']

                    # if debug enabled, print username password and url.
                    if dbg:
                        print(blog_username, blog_password, blog_url)

                    # ask whether to accept the current username?
                    
                    if fromvim:
                        vimcmd = "input('Use username " + blog_username + "? (y/n)')"
                        if dbg:
                            print(vimcmd)
                        useracceptkey = vim.eval(vimcmd)
                    else:
                        # if called from shell
                        useracceptkey = raw_input('Use username ' + blog_username + '? (y/n)')
                        
                    if useracceptkey == 'y':
                        # set handler using the newly gained credentials
                        handler = xmlrpclib.ServerProxy(blog_url).wp
                        blog_login_success = blog_test()
                        acceptkey = True if blog_login_success else False
                        # to delete, run gk.item_delete_sync(keyring,item_id)
                        # item_id can be found using key.item_id
                    
            if (not foundkeys) or (not acceptkey): 
                # if not found any keys or acceptkey failed due to failed login
                sys.stdout.write("Creating new user\n")

            # the loop runs whether or not keys were found.
            # the loop accepts username, password and url and tries to list blog entries. If it works, it creates a new item. If not, it asks if you want to reenter password.

            reenter_login = "y"
            # if blog_login_success is true if the keyfound is succesful, will not run the loop.
            while (not blog_login_success) and reenter_login == "y":
                # raw input will not work inside vim. so we have to call this section as an external shell python script.
                if fromvim:
                    blog_username = vim.eval("input('Enter username: ')")
                    # mismatch quotes to get vim.eval to work correctly; like bash
                    # To self: see how to create a password prompt in python. This will display plaintext.
                    blog_password = vim.eval("input('Enter password: ')")
                    # if the user hits enter, the default url is accepted. 
                    # https is needed for wordpress.com
                    default_url = 'https://' + blog_username + '.wordpress.com/xmlrpc.php'
                    command = 'input("Enter url (' + default_url + '): ")'
                    blog_url = vim.eval(command) or default_url
                    # convert the string to a boolean
                    enable_tags = bool(vim.eval("input('Enable tags? [True/False]')")) or True
                    # ive tested the blog_url statement out. it picks default_url if you just hit enter.
                else:
                    # shell version of above commands
                    blog_username = raw_input('Enter username: ')
                    blog_password = raw_input('Enter password: ')
                    default_url = 'https://' + blog_username + '.wordpress.com/xmlrpc.php'
                    blog_url = raw_input("Enter url (" + default_url + "): ") or default_url
                    enable_tags = raw_input('Enable tags? [True/False]') or False
                if dbg:
                    enable_tags = vim.eval("input('Enable tags? ')")
                    print (blog_username, blog_password, blog_url )

                # (re)set handler
                handler = xmlrpclib.ServerProxy(blog_url).wp
                # test if the blog works.
                blog_login_success = blog_test()
                if not blog_login_success:
                    # you might choose to not reenter even if blog_test failed.
                    if fromvim:
                        reenter_login = vim.eval("input('blog list failed. reenter details? (y/n)')")
                    else:
                        reenter_login = raw_input('blog list failed. reenter details? (y/n)')
                else:
                    #if blog_works
                    sys.stdout.write("Blog test succesful. Creating new keyring item.")
                    atts = {'username':blog_username,
                            'url':blog_url,
                            'appname':APP_NAME,
                            'enable_tags': str(enable_tags)
                            }
                    # see my notes or the gnome project documentation for item_crete_sync parameters.
                    gk.item_create_sync(KEYRING_NAME,gk.ITEM_GENERIC_SECRET,blog_username + '@' + blog_url,atts,blog_password,True)
                    # the last True argument means that if the item already exists, update it.
                    # the outer while ends now
                #endif
            #end while
        else:
            # if KEYRING_NAME does not exist, display error message.
            sys.stderr.write('Keyring',KEYRING_NAME,'not found. Please create keyring, or disable keyring and set blog details in blog.vim.')
    except:
        # output abstract error and output function name
        sys.stderr.write('Error in blog_set_keyring_info')

def blog_edit_off():
  global edit
  if edit:
    edit = 0
    #for i in ["i","a","s","o","I","A","S","O"]:
      #vim.command('map '+i+' <nop>')

def blog_edit_on():
    global edit
    if not edit:
        edit = 1
        # unmap these things? why? I don't know the purpose of this function.
        for i in ["i","a","s","o","I","A","S","O"]:
            vim.command('unmap '+i)

def blog_send_post():
  global localtempdir
  if not blog_login_success:
      blog_init()
      # if init cannot login, it will exit the script. if its succesful, it will not need to be run again.

  try:
    def get_line(what):
      start = 0
      while not vim.current.buffer[start].startswith('%'+what):
        # while not found % + what, increment the counter
        # for example, it could be %StrID 
        start +=1
      return start
    def get_meta(what): 
      start = get_line(what)
      end = start + 1
      while not vim.current.buffer[end][0] == '%':
        # while end does not start with %, increment; i.e., as soon as it starts with a %, end it
        # this means the current line of metadata has, which means tags can be split over several lines 
        end +=1
      return " ".join(vim.current.buffer[start:end]).split(":")[1].strip()
      # join all lines corresponding to the metadata element, split them and get the second word. The second word contains the data of the metadata. The first word is the metadata identifier.
        
    strid = get_meta("StrID")
    post_title = get_meta("Title")
    # self explanatory
    cats = [i.strip() for i in get_meta("Cats").split(",")]
    # make a list of categories
    if enable_tags:
      tags = get_meta("Tags")
    # get tags

    text_start = 0
    while not vim.current.buffer[text_start] == "%========== Content ==========":
      text_start +=1
    #endwhile

    # increment if possible so that its not in the %==Content line anymore
    text_start = min(text_start + 1, len(vim.current.buffer))

    text = '\n'.join(vim.current.buffer[text_start:])
    # increment the counter until you get to the content identifier line. Load the text of the buffer into the text variable.
    # I previously made several file conversions using text and pandoc. See old backup of blog.py

    content = text
    # sys.stderr.write(content) # use for debugging in vim only
    # read the converted html file into contents

    # for debugging, print out what exactly happens in the post

    if enable_tags:
      post = {
        'post_title': title,
        'description': content,
        'categories': cats,
        'mt_keywords': tags
      }
    else:
      post = {
        'post_title': title,
        'description': content,
        'categories': cats,
      }

    sys.stdout.write("About to send blog post \n")

    if strid == '':
      # if there is no str id, create a new post
      sys.stdout.write("There is no strid, will use handler to create new post\n")

      strid = handler.newPost(0, blog_username,
        blog_password, post)
      sys.stdout.write("There is no strid, will use handler to create new post\n")

      # update strID string in the metadata of current buffer.
      vim.current.buffer[get_line("StrID")] = "%StrID : "+strid
    else:
      handler.editPost(0, blog_username,
        blog_password, post, strid)
    sys.stdout.write("Successfully sent post\n")

    vim.command('set nomodified')
  #end try region
  except:
    sys.stderr.write("An error has occured in the python function blog_send_post\n")
    traceback.print_exc(file=sys.stdout)
#end blog_send_post

def blog_new_post():
  if not blog_login_success:
      blog_init()
      # if init cannot login, it will exit the script. if its succesful, it will not need to be run again.
  def blog_get_cats():
    # I don't understand what this is doing. I've kept it in there.
    l = handler.getTerms('', blog_username, blog_password,'category')
    s = ""
    for i in l:
        s = s + (i["description"].encode("utf-8"))+", "
    if s != "": 
        return s[:-2]
    else:
        return s
  del vim.current.buffer[:]
  blog_edit_on()
  #vim.command("set syntax="+VIMSYNTAX)
  #vim.command("set filetype="+VIMFILETYPE)
  vim.command("set syntax=markdown")
  vim.command("set filetype=markdown")
  # The latter command loads latexsuite

  vim.current.buffer[0] =   "%=========== Meta ============\n"
  vim.current.buffer.append("%StrID : ")
  vim.current.buffer.append("%Title : ")
  vim.current.buffer.append("%Cats  : "+blog_get_cats())
  if enable_tags:
    vim.current.buffer.append("%Tags  : ")
  vim.current.buffer.append("%========== Content ==========\n")
  vim.current.buffer.append("\n")
  vim.current.window.cursor = (len(vim.current.buffer), 0)
  vim.command('set nomodified')
  vim.command('set textwidth=0')
#end blog_new_post

def blog_open_post(id):
  global localtempdir
  if not blog_login_success:
      blog_init()
      # if init cannot login, it will exit the script. if its succesful, it will not need to be run again.
  try:
    # use getPost using the XMLRPC library. This is the wp section. 
    post = handler.getPost(0, blog_username, blog_password, id)
    # post seems to be a python dictionary referred to later.
    blog_edit_on()
    # I don't know what this function does as yet, but it seems to enable editing the file by unmapping some keys.
    vim.command("set syntax="+VIMSYNTAX)
    vim.command("set filetype="+VIMFILETYPE)
    # this sets the filetype so that syntax highlighting is set correctly

    vim.command('set nomodified')
    # this sets the current buffer to "not as yet modified", even though the script has made changes to it.
    vim.command('set textwidth=0')

    del vim.current.buffer[:]
    vim.current.buffer[0] =   "%=========== Meta ============\n"
    # automatically cursor position is now after the first line.
    vim.current.buffer.append("%StrID : "+str(id))
    vim.current.buffer.append("%Title : "+(post["post_title"]).encode("utf-8"))
    # categories replaced by terms
    vim.current.buffer.append("%Cats  : "+",".join(post["terms"]).encode("utf-8"))
    if enable_tags:
      vim.current.buffer.append("%Tags  : "+(post["mt_keywords"]).encode("utf-8"))
    vim.current.buffer.append("%========== Content ==========\n")
    # done appending header line
    content = (post["description"]).encode("utf-8")

    for line in content.split('\n'):
      vim.current.buffer.append(line)
      # append the lines from the tex files into current buffer

    # find out where the text starts, and put the cursor there
    text_start = seek_content_beginning()
    # add extra blank line, of course
    vim.current.window.cursor = (text_start+1, 0)
  except:
    sys.stderr.write("An error has occured in the python function blog_open_post")
    traceback.print_exc(file=sys.stdout)
#end blog_open_post

def seek_content_beginning():
  # this is an important bit of code that seeks the start of the content
  text_start = 0
  found = False
  text_end = len(vim.current.buffer)
  while (not found) and text_start < text_end :
    # increment the counter until the % == Content tag is found.
    if vim.current.buffer[text_start] == "%========== Content ==========":
      found = True
    text_start +=1
  #endwhile

  # move to line after the content tag, so increment text_start
  # increment it only if not at end of buffer
  text_start = min(text_start + 1,text_end)
  return text_start

def blog_list_edit():
  if not blog_login_success:
      blog_init()
      # if init cannot login, it will exit the script. if its succesful, it will not need to be run again.
  try:
    row,col = vim.current.window.cursor
    id = vim.current.buffer[row-1].split()[0]
    blog_open_post(int(id))
  except:
    pass
    # the traceback gives errors
    #traceback.print_exc(file=sys.stdout)

def set_post_type():
    # input post type. Usually set to page or post.
    vimcmd = "input('Enter post type (page, post): ')"
    if dbg:
        print(vimcmd)
    posttype=vim.eval(vimcmd)


def blog_list_posts():
  if dbg:
      sys.stdout.write("blog_login_success is: " + str(blog_login_success) + "\n")
      sys.stdout.write("blog_username is: " + str(blog_username) + "\n")
      sys.stdout.write("blog_username is: " + str(blog_username) + "\n")

  if not blog_login_success:
      blog_init()
      # if init cannot login, it will exit the script. if its succesful, it will not need to be run again.
  try:
    # to be deleted. I'm moving to the wp interface.
    #lessthan = handler.getRecentPosts('',blog_username, blog_password,1)[0]["postid"]
    #allposts = handler.getRecentPosts('',blog_username, blog_password,int(lessthan))
    # there is some code here to get the postid of the oldest post, and use its length to correctly format the numbers that show up in the post.
    allposts = handler.getPosts(0,blog_username,blog_password,{'post_type':posttype})
    # get length of postid for correct formatting
    size=len(allposts[0]['post_id'])

    del vim.current.buffer[:]
    vim.command("set syntax="+VIMSYNTAX)
    vim.current.buffer[0] = "%====== List of Posts ========="
    for p in allposts:
      #vim.current.buffer.append(("".zfill(size-len(p['postid'])).replace("0", " ")+p["postid"])+"\t"+(p["title"]).encode("utf-8"))
      vim.current.buffer.append(("".zfill(size-len(p['post_id'])).replace("0", " ")+p["post_id"])+"\t"+(p["post_title"]).encode("utf-8"))
      vim.command('set nomodified')
    # will reenable this when things are working
    #blog_edit_off()
    vim.current.window.cursor = (2, 0)
    vim.command('map <enter> :py blog_list_edit()<cr>')
  except:
    sys.stderr.write("An error has occured in blog_list_posts")
    if dbg:
        traceback.print_exc(file=sys.stdout)

def write_markdown_toc():
  # writes table of contents
  # perhaps modify for convenience, after adding TOC, move back to original location in file?
  global localtempdir, dbg

  try:
    # delete previous TOC
    # del_markdown_toc()
    # doctoc will auto refresh the TOC since it inserts tags automatically to demarcate the TOC section it generates.

    # seek beginning of blog post contents 
    text_start = seek_content_beginning() 
    # the content contains text_start to EOF
    content = vim.current.buffer[text_start:]

    # I could name the file using some sophisticated mechanism, but maybe not necessary
    tempfile = localtempdir + '/blogpost.md'
    f = open(tempfile,'w')
    # open temporary file in write mode

    # write content to file, we can iterate over the list content.
    for line in content:
    # write blog post contents to a file
      f.write(line + '\n')

    f.close()
    # close the file

    # run doctoc on the markdown file
    syscmd = 'doctoc ' + tempfile + ' 2>&1 > /tmp/doctout.out'
    # run the doctoc command on the file
    os.system(syscmd)
    # read the file into the buffer.
    
    # this will echo the whole tempfile, usually unnecessary
    #if dbg:
      #vim.command('echo tempfile')

    # clear old buffer
    del vim.current.buffer[text_start:]
    # do not need to append a blank line

    # start appending from markdown file with TOC
    f = open(tempfile,'r')
    # open the converted markdown file
    for line in f:
      vim.current.buffer.append(line)
    # move back to start of document. this is the line after the content tag
    vim.current.window.cursor = (text_start, 0)

    # delete the DOCTOC string inserted that says, "generated by DOCTOC"
    if dbg:
      sys.stdout.write("searching for doctoc string")

    line=0
    found_doctoc = False
    while (not found_doctoc) and line <= len(vim.current.buffer):
      # run loop while the DOCTOCSTRING IS NOT FOUND
      if vim.current.buffer[line].find(DOCTOCSTRING) != -1:
        # the function returns -1 if not found
        found_doctoc = True
        vim.current.buffer[line] = vim.current.buffer[line].replace(DOCTOCSTRING,'')
        if dbg:
          sys.stderr.write("line number = " + str(line))
          sys.stderr.write(DOCTOCSTRING + '\n')
          sys.stderr.write(vim.current.buffer[line].replace(DOCTOCSTRING,'') + '\n')
          sys.stderr.write("found doctoc string")
        # replace the doctocstring with nothing
      else:
        #otherwise increment line counter
        line = line + 1
     #endwhile 

    # print error message if not found doctoc string
    #if dbg and (not found_doctoc):
      #sys.stderr.write("did not find doctoc string")

  except:
    sys.stderr.write("Error occured in write_markdown_toc")
    traceback.print_exc(file=sys.stdout)

def del_markdown_toc():
  # the markdown toc is generated by doctoc. This deletes it if necessary. I now just refresh it using doctoc, a nice little javascript program
  global TOC_START_STRING, TOC_END_STRING
  try:
    # first look for Table of contents signature, TOC start
    found_start = False
    found_end = False
    bufend_line = len(vim.current.buffer) - 1 #last line of buffer, = lenght of buffer array - 1

    toc_start = 0
    while (not found_start) and toc_start <= bufend_line:
      # increment the counter until the Table of contents
      if vim.current.buffer[toc_start] == TOC_START_STRING:
        found_start = True
        #if found, will not increment loop and will end
      else:
        toc_start +=1
    #endwhile

    # find TOC end
    if found_start:
      toc_end = min(toc_start+1,bufend_line)
      while (not found_end) and toc_end <= bufend_line:
        # increment the counter until the Table of contents
        if vim.current.buffer[toc_end] == TOC_END_STRING:
          found_end = True
        else:
          toc_end +=1

    # if both tags are found, then toc_start <= bufend_line and toc_end <= bufend_line + 1
    # add extra +1 to toc_end because of python interval convention [a,b)
    if found_start and found_end:
      # if toc_end is at buffer end line + 1, make sure we dont go out of bounds
      #sys.stderr.write("toc_start " + str(toc_start) + "toc_end " + str(toc_end) )
      del vim.current.buffer[toc_start:min(toc_end,bufend_line)+1]
    else: 
      sys.stderr.write("Matching table of contents tags not found")

  except:
    sys.stderr.write("Error occured in del_markdown_toc")
    traceback.print_exc(file=sys.stdout)

