import web.template
import json
import zipfile
import cStringIO
import hashlib
import os
import time
import sys
import xml.etree.ElementTree as ET
import argparse

class Commit(object):
    def __init__(self, commit_id, commitDetails):
      self.id = commit_id;
      self.commitDetails = commitDetails;
    def cid(self):
      return self.id;
    def files(self):
      return self.commitDetails["files"];  
    def remove_file(self, filename):
      if filename in commitDetails["files"]:
          del commitDetails["files"][filename];
    def parent(self):
      return self.commitDetails["parent"];
    def setParent(self, parent):
      self.commitDetails["parent"] = parent;
      
    def __str__(self):
      return "{0}:{1}".format(self.id, self.commitDetails)
    @classmethod
    def from_file(cls, id, file):
      return cls("{0}".format(id), json.loads(file.read()))  
    @classmethod
    def from_id(cls, id):
      return cls.from_file(id, open("{0}.json".format(id), "r"))

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

    def removedFiles(self):
        return self.m_removedFiles;
    def newFiles(self):
        return self.m_newFiles;
    def modifiedFiles(self):
        return self.m_modifiedFiles;        

    def fileChanged(self,fileName):import json

class EV3Project(object):
    def __init__(self, name):
        self.name = name;
        self.head = "";
        try:
           with open("project.json", "r") as project_file:
               data = json.loads(project_file.read()) 
               self.head = data["head"]
        except:
           pass   
    def findNextCommit(self):
        id = 1;
        while(os.path.isfile("{0}.json".format(id))):
           id = id + 1;
        return str(id);  

    def getEV3Data(self, commit):
        variables = {}
        programs = []
        myblockdefs = []
        medias = []

        ev3Contents = cStringIO.StringIO()
        render = web.template.render('HTMLTemplates/');
        
        with zipfile.ZipFile(ev3Contents, "a", zipfile.ZIP_DEFLATED, False) as zf:
            # so we can keep track of the commit this is from
            zf.writestr("ev3hub.json", '{{"fromCommit": "{0}","project":"{1}"}}'.format(commit.cid(), self.name))
            for filename in commit.files():
                if commit.files()[filename] == "":
                    varInfo = filename.split(':', 1);
                    variables[varInfo[1]] = varInfo[0]
                else:
                    with open("repo/" + commit.files()[filename], 'r') as file:
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
            zf.writestr('Project.lvprojx', str(render.lvprojx(sorted(programs,key=unicode.lower), sorted(myblockdefs,key=unicode.lower), variables, sorted(medias,key=unicode.lower), False)))
     
            for zfile in zf.filelist:
                zfile.create_system = 0
            zf.close()
        return ev3Contents.getvalue();
        
    def uploadCommit(self, ev3data, comment, who, host):
        files = {};
        parent = "";

        in_memory_zip = cStringIO.StringIO(ev3data)
        with zipfile.ZipFile(in_memory_zip, "r", zipfile.ZIP_DEFLATED, False) as zf:
            for fileName in zf.namelist():
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
                    if not os.path.isfile("repo/"+m.hexdigest()):
                        data = zf.read(fileName)
                        with open("repo/"+m.hexdigest()), "wb" as outfile:
                            outfile.write(data)
        commit = {"parent" : parent, "time" : time.time(), "name" : who, "host" : host, "comment" : comment, "files" : files}
        
        id = self.findNextCommit();
        with open("{0}.json".format(id), "w") as outfile:
            json.dump(commit, outfile) 
        return id;       
    
    def find_common_parent(self, commit1, commit2):
        parents1 = [commit1.cid()]
        parents2 = [commit2.cid()]
               
        while not set(parents1) & set(parents2):
            print "{0}:{1} - {2}.{3}".format(parents1, parents2,commit1.cid(),commit2.cid())
            if(commit1.parent()):
                commit1 = Commit.from_id(commit1.parent())
                parents1.append(commit1.cid())
            if(commit2.parent()):
                commit2 = Commit.from_id(commit2.parent())
                parents2.append(commit2.cid())
            if not commit1.parent() and not commit2.parent():
                return "";   # no parent        
        return (set(parents1) & set(parents2)).pop()
    
    def merge(self, cid):
        data = {};
        errors = [];

        if self.head == "":
            self.head = cid;
            data["head"] = self.head;
        else:
            head_commit = Commit.from_id(self.head)
            id_commit = Commit.from_id(cid)
            # find common parent
            parent_cid = self.find_common_parent(head_commit, id_commit)
            print "head={0},id={1},parent={2}".format(self.head, id, parent_cid) 
            if (parent_cid == "") or (self.head == parent_cid):   # if you are uploading projects not using ev3hub treat as if you are directly after head
                data["head"] = id;   
                print "moving head"
            else:
                print "merging?"
# TODO: locking??
                parent_commit = Commit.from_id(parent_cid)
                changes_to_head = Changeset(parent_commit, head_commit)
                changes_to_commit = Changeset(parent_commit, id_commit)                      
                proposed_head_commit = head_commit;
                
                print "Changes_to_head:{0}".format(changes_to_head)
                print "Changes_to_commit:{0}".format(changes_to_commit)
              
                for filename in changes_to_commit.newFiles():
                    if filename in changes_to_head.newFiles():   # should check for same SHA here
                        errors.append("{0} added in both").format(filename)
                    else:
                        proposed_head_commit.files()[filename] = id_commit.files()[filename];
                for filename in changes_to_commit.modifiedFiles():
                    if filename in changes_to_head.modifiedFiles():   # should check for same SHA here
                        errors.append("{0} modified in both").format(filename)
                    else:
                        proposed_head_commit.files()[filename] = id_commit.files()[filename];    
                for filename in changes_to_commit.removedFiles():
                    if (filename in changes_to_head.modifiedFiles()):
                        proposed_head_commit.remove_file(filename)                    
                if not errors:
                    new_id = self.findNextCommit();
                    newCommit = {"parent" : self.head, "time" : time.time(), "name" : "EV3Hub", "host" : "", "comment" : "Auto-merged from {0}".format(cid), 
                                 "files" : proposed_head_commit.files()}
                    with open("{0}.json".format(new_id), "w") as outfile:
                        json.dump(newCommit, outfile)
                    data["head"] = new_id;
                    self.head = new_id;
                
        with open("project.json", "w") as project_file:
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
    ev3P = EV3Project("test")
    id = ev3P.uploadCommit(ev3contents, args.comment, "author", "honeycrisp")
    merge_errors = ev3P.merge(id)
    if merge_errors:
       print merge_errors
    else:
       print "Successful merge!"    
    
    commit = Commit.from_id(ev3P.head)
    with open("out.zip", "w") as outfile:
       outfile.write(ev3P.getEV3Data(commit))

