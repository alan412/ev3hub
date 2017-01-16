from mako.template import Template
import zipfile
import os
import json
import time
import cStringIO
import hashlib
import argparse
import xml.etree.ElementTree as ET

class Commit(object):
    def __init__(self, path, commit_id, commitDetails): 
      self.path = path;
      self.filename = os.path.join(path, "{0}.json".format(commit_id))
      
      self.commit_id = commit_id;
      self.commitDetails = commitDetails;
     
    def cid(self):
      return self.commit_id;
    def files(self):
      return self.commitDetails["files"];  
    def getSHA(self, filename):
      try:
          return self.commitDetails["files"][filename]
      except:
          return ""      
    def remove_file(self, filename):
      if filename in commitDetails["files"]:
          del commitDetails["files"][filename];
    def parent(self):
      return self.commitDetails["parent"];
    def time(self):
      return self.commitDetails["time"];
    def timeStr(self):
      return time.strftime("%a %b %d, %Y %I:%M %p %Z", time.localtime(self.time()));
    def name(self):
      return self.commitDetails["name"];
    def host(self):
      return self.commitDetails["host"];
    def comment(self):
      return self.commitDetails["comment"];
    def save(self):
      if self.path:
          with open(self.filename, "w") as outfile:
              json.dump(self.commitDetails, outfile)      
    def delete(self):
       if self.filename:
           os.remove(self.filename);
           self.filename = ''
           self.path = ''
    def get_ev3_data(self, projName):
        variables = {}
        programs = []
        myblockdefs = []
        medias = []
        
        ev3Contents = cStringIO.StringIO()
        
        ev3_template = Template(filename='HTMLTemplates/lvprojx.html');
                
        with zipfile.ZipFile(ev3Contents, "a", zipfile.ZIP_DEFLATED, False) as zf:
            # so we can keep track of the commit this is from
            zf.writestr("ev3hub.json", '{{"fromCommit": "{0}","project":"{1}"}}'.format(self.cid(), projName))
            for filename in self.files():
                if self.files()[filename] == "":
                    varInfo = filename.split(':', 1);
                    variables[varInfo[1]] = varInfo[0]
                else:
                    repo_filename = os.path.join(self.path, "repo", self.files()[filename])
                    with open(repo_filename, 'r') as file:
                        zf.writestr(filename, file.read())    
                    file_parts = filename.split('.',1);
     
                    basename = file_parts[0];
                    ext = file_parts[-1];
                    
                    if ext.startswith('ev3p'):
                        if ext == 'ev3p.mbxml':
                            myblockdefs.append(basename + '.ev3p')
                        else:
                          programs.append(filename)
                    elif ext in ['rgf', 'rsf', 'rtf']:
                        medias.append(filename)

            for myblock in myblockdefs:
                programs.remove(myblock)
                
            # generate lvprojx.proj file here
            lvprojx_data = ev3_template.render(programs= sorted(programs, key=unicode.lower), 
                                               myblockdefs= sorted(myblockdefs, key=unicode.lower),
                                               vars= variables,
                                               medias= sorted(medias, key=unicode.lower),
                                               daisychain= False,
                                               strict_underfined=True)                
            zf.writestr('Project.lvprojx', lvprojx_data)
            
            for zfile in zf.filelist:
                zfile.create_system = 0
            zf.close()
        return ev3Contents.getvalue();
    
    @classmethod
    def from_ev3file(cls, path, cid, ev3data, comment, who, host, project_name):    
        files = {};
        parent = 0;
        in_memory_zip = cStringIO.StringIO(ev3data)
        with zipfile.ZipFile(in_memory_zip, "r", zipfile.ZIP_DEFLATED, False) as zf:
            for fileName in zf.namelist():
                if zf.getinfo(fileName).file_size > 1024*1024*1024:  # don't allow larger than 1MB
                    raise zipfile.BadZipfile 
                if fileName == "ev3hub.json":
                    with zf.open("ev3hub.json", 'r') as json_file:
                        data = json.loads(json_file.read())
                        if data["project"] == project_name:
                           parent = data["fromCommit"]
                elif fileName == "Project.lvprojx":
                    with zf.open('Project.lvprojx', 'r') as project_file:
                      new_projxml = ET.fromstring(project_file.read())
                    for ns in new_projxml:
                      if ns.attrib['Name'] == 'Default':
                        for sns in ns[0]:
                          if 'ProjectSettings' in sns.tag:
                            for ssns in sns:
                              if 'NamedGlobalData' in ssns.tag:
                                for var in ssns:
                                  files[var.attrib['Type'] + ':' + var.attrib['Name']] = ""
                else:  
                    contents = zf.read(fileName)
                    m = hashlib.sha1()
                    m.update(contents)
                    files[fileName] = m.hexdigest()
                    destination_filepath = os.path.join(path, "repo/"+m.hexdigest())
                    if not os.path.isfile(destination_filepath):
                        with open(destination_filepath, "wb") as outfile:
                            outfile.write(zf.read(fileName))
            commit = cls(path, cid, {"parent" : parent, "mergedFrom" : 0, "time" : time.time(), "name" : who, "host" : host, "comment" : comment, "files" : files})
            commit.save()
            return commit   
    def __str__(self):
      return "{0}:{1}".format(self.commit_id, self.commitDetails)

    @classmethod
    def from_id(cls, project_path, cid):
      if "{0}".format(cid) == "0":
          commitDetails = {"parent" : 0, "mergedFrom" : 0, "time" : time.time(), "name" : "", "host" : "", "comment" : "", "files" : {}}
          return cls("", cid, commitDetails)   # this is only for the null parent.

      with open(cls.file_from_id(project_path, cid), "r") as file:
          data = json.loads(file.read())
          return cls(project_path, cid, data)
      
      return None
    @classmethod
    def from_merge(cls, project_path, head, newCid, cid, files):
        commitDetails = {"parent" : head, "mergedfrom" : cid, "time" : time.time(), "name" : "EV3Hub", "host" : "", "comment" : "Auto-merged from {0}".format(cid), 
                                 "files" : files}

        return cls(project_path, newCid, commitDetails)
      
    @classmethod
    def file_from_id(cls, path, cid):
      return os.path.join(path, "{0}.json".format(cid));
          
class Changeset(object):
    def __str__(self):
      return "Removed: {0}\nNew: {1}\nModified: {2}\n".format(self.m_removedFiles, self.m_newFiles, self.m_modifiedFiles)
    
    def __init__(self, oldCommit, newCommit):
        self.m_removedFiles = [];
        self.m_newFiles = [];
        self.m_modifiedFiles = [];
        
        oldCommitFiles = oldCommit.files();
        newCommitFiles = newCommit.files();
        
        for newF in newCommitFiles:
           new_filename = newF[0];
           if newF in oldCommitFiles:
               if(newCommitFiles[newF] != oldCommitFiles[newF]):
                   self.m_modifiedFiles.append(newF);
           else:
              self.m_newFiles.append(newF);    
        
        for oldF in oldCommitFiles:
            if oldF not in newCommitFiles:
                self.m_removedFiles.append(oldF);     
    def different(self):
        if (self.m_removedFiles == []) and (self.m_newFiles == []) and (self.m_modifiedFiles == []):
            return False
        else:
            return True
    def removedFiles(self):
        return self.m_removedFiles;
    def newFiles(self):
        return self.m_newFiles;
    def modifiedFiles(self):
        return self.m_modifiedFiles; 
        
        
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Test ev3commit code")
    parser.add_argument('file1')

    args = parser.parse_args()   
    
    with open(args.file1, 'r') as ev3File:
        ev3contents = ev3File.read()
        commit1 = Commit.from_ev3file('testDir', 1, ev3contents, "comment", "who", "host", "project");  

    commit2 = Commit.from_id('testDir', 1)
    with open("out.zip", "w") as outfile:
       outfile.write(commit2.get_ev3_data("project"))
       