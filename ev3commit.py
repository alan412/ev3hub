from mako.template import Template
import zipfile
import os
import json
import time
import cStringIO
import hashlib
import xml.etree.ElementTree as ET

class Commit(object):
    def __init__(self, commit_id, commitDetails):
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
      
    def get_EV3_data(self, projName, fullpath):
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
                    with open(fullpath + self.files()[filename], 'r') as file:
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
       
    def __str__(self):
      return "{0}:{1}".format(self.commit_id, self.commitDetails)
    @classmethod
    def from_file(cls, cid, file):
      return cls(cid, json.loads(file.read()))  
    
    @classmethod
    def from_id(cls, cid, path):
      if "{0}".format(cid) == "0":
          commitDetails = {"parent" : 0, "mergedFrom" : 0, "time" : time.time(), "name" : "", "host" : "", "comment" : "", "files" : {}}
          return cls(cid, commitDetails)
      return cls.from_file(cid, open(cls.file_from_id(path, cid), "r"))
      
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