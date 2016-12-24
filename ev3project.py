import json
import os
import time
import sys
import argparse
from operator import methodcaller
from ev3commit import Commit, Changeset
       
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
        commit_id = cid;
        if cid == "head":
            commit_id = self.head;
        return Commit.from_id(commit_id, self.path).get_EV3_data(self.name, self.fullpath("repo/"))
        
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
        parents1 = ["{0}".format(commit1.cid())]
        parents2 = ["{0}".format(commit2.cid())]
        
        while not set(parents1) & set(parents2):
#            print "{0}:{1} - {2}.{3}".format(parents1, parents2,commit1.cid(),commit2.cid())
            if(commit1.parent()):
                commit1 = Commit.from_id(commit1.parent(), self.path)
                parents1.append("{0}".format(commit1.cid()))
            if(commit2.parent()):
                commit2 = Commit.from_id(commit2.parent(), self.path)
                parents2.append("{0}".format(commit2.cid())) 
            elif commit1.parent() == commit2.parent():   # in this case they are both 0
                parents1.append("0");
                parents2.append("0");
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
#            print "Head:{0} ID: {1} Parent {2}".format(self.head, cid, parent_cid) 
#            print "Changes_to_head:{0}".format(changes_to_head)
#            print "Changes_to_commit:{0}".format(changes_to_commit)
          
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

