from mako.template import Template
import json
import zipfile
import cStringIO
import hashlib
import os
import time
import sys
import xml.etree.ElementTree as ET
import argparse
from operator import methodcaller

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
    def mergedfrom(self):
      return self.commitDetails["mergedFrom"];
    def setParent(self, parent):
      self.commitDetails["parent"] = parent;
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
       
    def __str__(self):
      return "{0}:{1}".format(self.commit_id, self.commitDetails)
    @classmethod
    def from_file(cls, cid, file):
      return cls(cid, json.loads(file.read()))  
    
    @classmethod
    def from_id(cls, cid, path):
      if cid == 0:
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


class EV3Project(object):
    @classmethod
    def newProject(cls, user, name, ev3data, who, host):
        if os.path.exists(os.path.join(user, name)):
          return None;
        newP = cls(name, user);
        data = {}
        data["head"] = 1;
        data["failedMerges"] = [];
        newP.uploadCommit(ev3data, "Initial Commit", who, host);    
        with open(newP.fullpath("project.json"), "w") as project_file:
            json.dump(data, project_file);      
        return newP
     
    def fullpath(self, filename):
        return os.path.join(self.path, filename) 
    
    def __init__(self, name, user):
        self.name = name;
        self.user = user;   # not sure why I am saving this....
        self.path = os.path.join('data', user, name)
        self.failedMerges = [];
        self.head = 1;
        
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            os.makedirs(self.fullpath('repo'))
            
        try:
           with open(self.fullpath("project.json"), "r") as project_file:
               data = json.loads(project_file.read()) 
               self.head = data["head"]
               self.failedMerges = data["failedMerges"]
               if(self.failedMerges is None):
                   self.failedMerges = []
        except:
           pass   
    def getCommit(self, cid):
        return Commit.from_id(cid, self.path)
        
    def getListOfCommits(self):
        commits = [];
        cid = 1;

        while(os.path.isfile(Commit.file_from_id(self.path, cid))):
            commits.append(Commit.from_id(cid, self.path))
            cid = cid + 1
        return sorted(commits, key=methodcaller('time'), reverse=True)                
               
    def findNextCommit(self):
        cid = 1;
        while(os.path.isfile(Commit.file_from_id(self.path, cid))):
           cid = cid + 1;
        return str(cid);  
    
    def download(self, cid):
        if cid == "head":
            return self.getEV3Data(Commit.from_id(self.head, self.path))
        else:
            return self.getEV3Data(Commit.from_id(cid, self.path))
            
    def getEV3Data(self, commit):
        variables = {}
        programs = []
        myblockdefs = []
        medias = []

        ev3Contents = cStringIO.StringIO()
        
        ev3_template = Template(filename='HTMLTemplates/lvprojx.html');
        
        with zipfile.ZipFile(ev3Contents, "a", zipfile.ZIP_DEFLATED, False) as zf:
            # so we can keep track of the commit this is from
            zf.writestr("ev3hub.json", '{{"fromCommit": "{0}","project":"{1}"}}'.format(commit.cid(), self.name))
            for filename in commit.files():
                if commit.files()[filename] == "":
                    varInfo = filename.split(':', 1);
                    variables[varInfo[1]] = varInfo[0]
                else:
                    with open(self.fullpath("repo/" + commit.files()[filename]), 'r') as file:
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
        
    def uploadCommit(self, ev3data, comment, who, host):
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
                        if data["project"] == self.name:
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
                    if not os.path.isfile(self.fullpath("repo/"+m.hexdigest())):
                        data = zf.read(fileName)
                        with open(self.fullpath("repo/"+m.hexdigest()), "wb") as outfile:
                            outfile.write(data)
        commit = {"parent" : parent, "mergedFrom" : 0, "time" : time.time(), "name" : who, "host" : host, "comment" : comment, "files" : files}
        
        cid = self.findNextCommit();
        with open(self.fullpath("{0}.json".format(cid)), "w") as outfile:
            json.dump(commit, outfile) 
        return cid;       
    
    def find_common_parent(self, commit1, commit2):
        parents1 = [commit1.cid()]
        parents2 = [commit2.cid()]
        
        while not set(parents1) & set(parents2):
#            print "{0}:{1} - {2}.{3}".format(parents1, parents2,commit1.cid(),commit2.cid())
            if(commit1.parent()):
                commit1 = Commit.from_id(commit1.parent(), self.path)
                parents1.append(commit1.cid())
            if(commit2.parent()):
                commit2 = Commit.from_id(commit2.parent(), self.path)
                parents2.append(commit2.cid()) 
            elif commit1.parent() == commit2.parent():   # in this case they are both 0
                parents1.append(0);
                parents2.append(0);
                
        return (set(parents1) & set(parents2)).pop()   
    
    def merge(self, cid):
        data = {};
        errors = [];
        
        if not self.head:
            self.head = cid;
        else:    
            head_commit = Commit.from_id(self.head, self.path)
            id_commit = Commit.from_id(cid, self.path)
            # find common parent
            parent_cid = self.find_common_parent(head_commit, id_commit)

            parent_commit = Commit.from_id(parent_cid, self.path)
            changes_to_head = Changeset(parent_commit, head_commit)
            changes_to_commit = Changeset(parent_commit, id_commit)                      
            proposed_head_commit = head_commit;
            
            print "Changes_to_head:{0}".format(changes_to_head)
            print "Changes_to_commit:{0}".format(changes_to_commit)
          
            for filename in changes_to_commit.newFiles():
                if (filename in changes_to_head.newFiles()) and (head_commit.getSHA(filename) != id_commit.getSHA(filename)):   
                    errors.append("{0} added in both".format(filename))
                else:
                    proposed_head_commit.files()[filename] = id_commit.files()[filename];
            for filename in changes_to_commit.modifiedFiles():
                if (filename in changes_to_head.modifiedFiles()) and (head_commit.getSHA(filename) != id_commit.getSHA(filename)):    
                    errors.append("{0} modified in both".format(filename))
                else:
                    proposed_head_commit.files()[filename] = id_commit.files()[filename];    
            for filename in changes_to_commit.removedFiles():
                if (filename in changes_to_head.modifiedFiles()):
                    proposed_head_commit.remove_file(filename)                    
            print "Errors: {0}".format(errors)
            
            if not errors:
                new_id = self.findNextCommit();
                newCommit = {"parent" : self.head, "mergedfrom" : cid, "time" : time.time(), "name" : "EV3Hub", "host" : "", "comment" : "Auto-merged from {0}".format(cid), 
                             "files" : proposed_head_commit.files()}
                cs = Changeset(Commit(new_id, newCommit), id_commit)             
                if cs.different():
                    with open(self.fullpath("{0}.json".format(new_id)), "w") as outfile:
                        json.dump(newCommit, outfile)
                    data["head"] = new_id;
                    self.head = new_id;
                else:
                    data["head"] = cid;
                    self.head = cid;
            else:
                self.failedMerges.append(cid)
        data = {}
        data["head"] = self.head;
        data["failedMerges"] = self.failedMerges        
        with open(self.fullpath("project.json"), "w") as project_file:
           json.dump(data, project_file);
        
        return errors;
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Test ev3project code")
    parser.add_argument('file')
    parser.add_argument('-c', "--comment", help="comment for checkin")
    args = parser.parse_args()   
    
    commit_filename = args.file
    with open(commit_filename, 'r') as ev3File:
        ev3contents = ev3File.read()
    ev3P = EV3Project("test", "user")
    cid = ev3P.uploadCommit(ev3contents, args.comment, "author", "honeycrisp")
    merge_errors = ev3P.merge(cid)
    if merge_errors:
       print merge_errors
    else:
       print "Successful merge!"    
    
    commit = Commit.from_id(ev3P.head, ev3P.path)
    with open("out.zip", "w") as outfile:
       outfile.write(ev3P.getEV3Data(commit))

