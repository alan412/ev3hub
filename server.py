import web
import time
import os
import json
import zipfile
import tempfile
import copy
import filecmp
import thread
import xml.etree.ElementTree as ET

urls = (
  '/about', 'about',
  '/login', 'login',
  '/logout', 'logout',
  
  '/overview', 'index',
  '/overview/', 'index',
  '/overview/(.+)', 'index',

  '/commits/(.+)', 'commits',

  '/finish_commit/(.+)', 'finish_commit',

  '/download_project/(.+)/(.+)', 'download_project',
  '/download_project/(.+)', 'download_project',

  '/upload_project', 'upload_project',

  '/create_project', 'create_project',

  '/(.+)', 'login',
  '/', 'login'
)
app = web.application(urls, globals())
render = web.template.render('HTMLTemplates/', base = '', globals={
  'web': web
})
variable_types = {'TVARIABLE':'X3String', 'NAVARIABLE':'X3NumericArray', 'LAVARIABLE':'X3BooleanArray', 'NVARIABLE':'X3Numeric', 'LVARIABLE':'X3Boolean'}
flipped_variable_types = dict((value, key) for key, value in variable_types.iteritems())
port = 80
with open('settings.json', 'r') as settingsfile:
  settings = json.loads(settingsfile.read())
  registered_users = settings['logins']
  try:
    port = int(settings['port'])
  except:
    port = 80

def auth_app_processor(handle):
  global web
  web.ctx.request_time = time.time()
  web.ctx.use_layout = True
  try:
    web.ctx.mobile = False
    web.ctx.mobile = detect_mobile_browser(web.ctx.env['HTTP_USER_AGENT'])
  except: web.ctx.mobile = False
  cookie = web.cookies(username = None, password = None)
  web.ctx.username = cookie.username

  if not web.ctx.path in ['/login', '/about']:
    if cookie.username in registered_users:
      if registered_users[cookie.username] != cookie.password:
        web.ctx.username = None
        raise web.seeother('/login')
        return
    else:
      web.ctx.username = None
      raise web.seeother('/login')
      return
    web.ctx.username = cookie.username
     
  return handle()

app.add_processor(auth_app_processor)

class login:
  def GET(self):
    if web.ctx.username and web.ctx.username!='None':
      raise web.seeother('/overview')
    else:
      return render.login()

  def POST(self):
    i = web.input()
    if i.username in registered_users:
      if i.password == registered_users[i.username]:
        web.setcookie('username', i.username, expires=3600*24*365)
        web.setcookie('password', i.password, expires=3600*24*365)
        raise web.seeother('/overview')
      else:
        web.setcookie('username', None)
        web.setcookie('password', None)
        raise web.seeother('/login')
        return
    else:
      web.setcookie('username', None)
      web.setcookie('password', None)
      raise web.seeother('/login')
      return
    
class logout:
  def GET(self):
    web.setcookie('username', None, expires=-1)
    web.setcookie('password', None, expires=-1)
    raise web.seeother('/login')

class index:
  def GET(self, arg=0):
    projects = []
    try:
      projects = os.listdir('Projects/'+web.ctx.username)
    except:
      projects = []
    return render.overview(sorted(projects))

class about:
  def GET(self, arg=0):
    return render.about()

class commits:
  def GET(self, project):
    with open('Projects/'+web.ctx.username+'/'+project+'/info.json') as infofile:
      return infofile.read()

class upload_project:
  def POST(self, arg=0, arg2=0):
    i = web.input(ev3file={})
    arcname = '0'
    
    with open('commits.json', 'r+') as commitFile:
      commits = json.loads(commitFile.read())
      commitFile.seek(0)
      arcname = str(int(max(commits, key=int))+1)
      commits[arcname] = [web.ctx.username, i.project]
      commitFile.write(json.dumps(commits))
      commitFile.truncate()
    with open('Commits/' + arcname+'.ev3', 'wb') as arcfile:
      arcfile.write(i.ev3file.value)
    
    raise web.seeother('/finish_commit/'+arcname)

class finish_commit:
  def GET(self, commit_id):
    commits = {}
    with open('commits.json', 'r') as commitFile:
      commits = json.loads(commitFile.read())
    try:
      if commits[str(commit_id)][0] == web.ctx.username:
        project_name = commits[str(commit_id)][1]
        try:os.rmdir('Commits/'+str(commit_id))
        except: pass
        '''
          for child in ev3file.infolist():
            print child
            ev3file.extract(child, path=str('Commits/'+str(commit_id)))'''
        with zipfile.ZipFile(str('Commits/'+str(commit_id))+'.ev3', 'r') as ev3file:
          to_be_added = []
          to_be_removed = []
          to_be_changed = []
          
          info = None
          with open('Projects/'+web.ctx.username+'/'+project_name+'/info.json') as infofile:
            info = json.loads(infofile.read())
          if info:
            previous_files = {}
            for i in range(len(info['changes'])):
              changeset = info['changes'][i]
              for added_file in changeset['added']:
                previous_files[added_file] = copy.deepcopy(i)
              for modded_file in changeset['changed']:
                previous_files[modded_file] = copy.deepcopy(i)
              for removed_file in changeset['removed']:
                try:
                  del previous_files[removed_file]
                except: pass

            new_projxml = None
            existing_variables = []
            with ev3file.open('Project.lvprojx', 'r') as project_file:
              new_projxml = ET.fromstring(project_file.read())
            for ns in new_projxml:
              if ns.attrib['Name'] == 'Default':
                for sns in ns[0]:
                  if 'ProjectSettings' in sns.tag:
                    for ssns in sns:
                      if 'NamedGlobalData' in ssns.tag:
                        for var in ssns:
                          if var.attrib['Name']+'.VARIABLE' in previous_files:
                            with open('Projects/'+web.ctx.username+'/'+project_name+'/'+str(previous_files[var.attrib['Name']+'.VARIABLE'])+'/'+var.attrib['Name']+'.VARIABLE', 'r') as existing_var:
                              if var.attrib['Type'] != existing_var.read().strip().rstrip():
                                to_be_changed.append([var.attrib['Name'], flipped_variable_types[var.attrib['Type']]])
                              else:
                                existing_variables.append([var.attrib['Name'], flipped_variable_types[var.attrib['Type']]])
                          else:
                            to_be_added.append([var.attrib['Name'], flipped_variable_types[var.attrib['Type']]])
                        break

            for f in previous_files:
              if f == 'Project.lvprojx': continue
              split_f = f.split('.',1)
              if split_f[-1] == 'VARIABLE':
                for var in to_be_added+to_be_changed+existing_variables:
                  if var[0] == split_f[0]:
                    break
                else:
                  with open('Projects/'+web.ctx.username+'/'+project_name+'/'+str(previous_files[f])+'/'+f) as varfile:
                    to_be_removed.append([split_f[0], flipped_variable_types[varfile.read().rstrip().strip()]])
              else:
                try:
                  with ev3file.open(f, 'r') as zippedfile:
                    with open('Projects/'+web.ctx.username+'/'+project_name+'/'+str(previous_files[f])+'/'+f, 'rb') as existing_file:
                      while(True):
                        zfr=zippedfile.read(1000)
                        efr=existing_file.read(1000)
                        
                        if zfr != efr:
                          to_be_changed.append(split_f)
                          break
                        if not zfr or not efr:
                          break
                    
                except: to_be_removed.append(f.split('.',1))
            for f in ev3file.namelist():
              if f == 'Project.lvprojx': continue
              if not f in previous_files:
                to_be_added.append(f.split('.',1))

          return render.finish_commit(project_name, to_be_added, to_be_removed, to_be_changed, '')
      else:
        return "Don't steal another team's work!!! >:("
    except KeyboardInterrupt:
      return "Something happened."

    


  def POST(self, commit_id):
    i = web.input()
    commits = {}
    project_name=''
    with open('commits.json', 'r') as commitFile:
      commits = json.loads(commitFile.read())
    try:
      if not commits[str(commit_id)][0] == web.ctx.username:
        return "Don't steal another team's work!!!! >:("
      else:
        project_name = commits[str(commit_id)][1]
    except:
      return "Don't steal another team's work!!!! >:("

    project_info = {}
    with open('Projects/'+web.ctx.username+'/'+project_name.strip('/')+'/info.json') as infofile:
      project_info = json.loads(infofile.read())
    what_to_commit = json.loads(i.whatItems)
    for r in range(len(what_to_commit['remove'])):
      split_what = what_to_commit['remove'][r].split('.',1)
      if split_what[-1] in variable_types:
        what_to_commit['remove'][r] = split_what[0]+'.VARIABLE'
    project_info['changes'].append({
      'time':time.time(),
      'description':i.description,
      'added':[],
      'removed':what_to_commit['remove'],
      'changed':[],
      'by':i.byName
      })

    def stoi(x):
      try: return int(x)
      except: return -10
    
    new_dir_name = str(int(max(os.listdir('Projects/'+web.ctx.username+'/'+project_name.strip('/')), key=stoi))+1)
    os.mkdir('Projects/'+web.ctx.username+'/'+project_name.strip('/')+'/'+new_dir_name)
    with zipfile.ZipFile(str('Commits/'+str(commit_id))+'.ev3', 'r') as ev3file:
      for file_to_add in what_to_commit['add']:
        if file_to_add.split('.',1)[-1] in variable_types:
          with open('Projects/'+web.ctx.username+'/'+project_name.strip('/')+'/'+new_dir_name+'/'+file_to_add.split('.',1)[0]+'.VARIABLE', 'w') as newfile:
            newfile.write(variable_types[file_to_add.split('.',1)[-1]])
            project_info['changes'][-1]['added'].append(file_to_add.split('.',1)[0]+'.VARIABLE')
        else:
          with ev3file.open(file_to_add, 'r') as zippedfile:
            with open('Projects/'+web.ctx.username+'/'+project_name.strip('/')+'/'+new_dir_name+'/'+file_to_add, 'wb') as newfile:
              newfile.write(zippedfile.read())
              project_info['changes'][-1]['added'].append(file_to_add)
      for file_to_change in what_to_commit['change']:
        if file_to_change.split('.',1)[-1] in variable_types:
          with open('Projects/'+web.ctx.username+'/'+project_name.strip('/')+'/'+new_dir_name+'/'+file_to_change.split('.',1)[0]+'.VARIABLE', 'w') as newfile:
            newfile.write(variable_types[file_to_change.split('.',1)[-1]])
            project_info['changes'][-1]['changed'].append(file_to_change.split('.',1)[0]+'.VARIABLE')
        else:
          with ev3file.open(file_to_change, 'r') as zippedfile:
            with open('Projects/'+web.ctx.username+'/'+project_name.strip('/')+'/'+new_dir_name+'/'+file_to_change, 'wb') as newfile:
              newfile.write(zippedfile.read())
              project_info['changes'][-1]['changed'].append(file_to_change)
    with open('Projects/'+web.ctx.username+'/'+project_name.strip('/')+'/info.json', 'w') as infofile:
      infofile.write(json.dumps(project_info))
    os.remove('Commits/'+str(commit_id)+'.ev3')
    del commits[str(commit_id)]
    with open('commits.json', 'w') as commitFile:
      commitFile.write(json.dumps(commits))
    return render.commit_success(project_name)

class download_project:
  def GET(self, project, phase='tip'):
    info = None
    with open('Projects/'+web.ctx.username+'/'+project.strip('/')+'/info.json') as infofile:
      info = json.loads(infofile.read())
    if info:
      files = {}
      for i in range(len(info['changes'])):
        changeset = info['changes'][i]
        for added_file in changeset['added']:
          files[added_file] = copy.deepcopy(i)
        for modded_file in changeset['changed']:
          files[modded_file] = copy.deepcopy(i)
        for removed_file in changeset['removed']:
          try:
            del files[removed_file]
          except: pass
        if phase != 'tip' and int(phase) <= i:
          break

      variables = {}
      programs = []
      myblockdefs = []
      medias = []
      filtered_files = {}
      for f in files:
        ext = f.split('.', 1)[-1]
        if ext == 'lvprojx':
          pass
        elif ext == 'VARIABLE':
          with open('Projects/'+web.ctx.username+'/'+project.strip('/')+'/'+str(files[f])+'/'+f) as varsetting:
            variables[f.split('.',1)[0]] = varsetting.read().rstrip().strip()
        elif ext.startswith('ev3p'):
          if ext == 'ev3p.mbxml':
            myblockdefs.append(f[:-6])
          elif not f.split('.', 1)[0]+'.ev3p.mbxml' in files:
            programs.append(f)
          filtered_files[f] = files[f]
        elif ext in ['rgf', 'rsf', 'rtf']:
          medias.append(f)
          filtered_files[f] = files[f]
        else:
          filtered_files[f] = files[f]

      #return filtered_files

      with tempfile.TemporaryFile(mode='w+b') as tmparc:
        with zipfile.ZipFile(tmparc, 'w') as archive:
          archive.writestr('Project.lvprojx', str(render.lvprojx(programs, myblockdefs, variables, medias, False)))
          for f in filtered_files:
            archive.write('Projects/'+web.ctx.username+'/'+project.strip('/')+'/'+str(filtered_files[f])+'/'+f, f)
        tmparc.seek(0)
        web.header('Content-Type','unknown')
        web.header('Content-disposition', 'attachment; filename=' + project.strip('/')+'.ev3')
        return tmparc.read() 
    else:
      web.ctx.status = '404 Not Found'
      return 'Error'

class create_project:
  def POST(self):
    i = web.input(ev3file={},public=False,description='',name='',by='')
    if not os.path.exists('Commits'):
      os.mkdir('Commits')
    if not os.path.exists('Projects/'+web.ctx.username):
      os.mkdir('Projects/'+web.ctx.username)
    if os.path.exists('Projects/'+web.ctx.username+'/'+i.name) :
      return 'Error: path already exists. :/'
    os.mkdir('Projects/'+web.ctx.username+'/'+i.name)
    os.mkdir('Projects/'+web.ctx.username+'/'+i.name+'/0')
    info = {'public':i.public,'changes':[{'added':[],'changed':[],'removed':[],'by':i.by,'description':'Initial Commit','time':time.time()}],'description':i.description}
    with open('Projects/'+web.ctx.username+'/'+i.name+'/start.ev3', 'wb') as ev3file:
      ev3file.write(i.ev3file.value)
    with zipfile.ZipFile('Projects/'+web.ctx.username+'/'+i.name+'/start.ev3', 'r') as ev3file:
      for f in ev3file.namelist():
        if f == 'Project.lvprojx':
          new_projxml = None
          existing_variables = []
          with ev3file.open('Project.lvprojx', 'r') as project_file:
            new_projxml = ET.fromstring(project_file.read())
          for ns in new_projxml:
            if ns.attrib['Name'] == 'Default':
              for sns in ns[0]:
                if 'ProjectSettings' in sns.tag:
                  for ssns in sns:
                    if 'NamedGlobalData' in ssns.tag:
                      for var in ssns:
                        info['changes'][0]['added'].append(var.attrib['Name']+'.VARIABLE')
                        with open('Projects/'+web.ctx.username+'/'+i.name+'/0/'+var.attrib['Name']+'.VARIABLE', 'w') as diskfile:
                          diskfile.write(var.attrib['Type'])
                      break
        else:
          info['changes'][0]['added'].append(f)
          with ev3file.open(f, 'r') as subfile:
            with open('Projects/'+web.ctx.username+'/'+i.name+'/0/'+f, 'wb') as diskfile:
              diskfile.write(subfile.read())
    
    with open('Projects/'+web.ctx.username+'/'+i.name+'/info.json', 'w') as infofile:
      infofile.write(json.dumps(info))
    raise web.seeother('/overview')
    return 'Success'

if __name__ == "__main__":
  import socket
  print "One of these might be your IP address: ",
  for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
    print ip,
  print ''
  print 'Webserver running for you on',
  func = app.wsgifunc()
  web.httpserver.runsimple(func, ('0.0.0.0', port))
