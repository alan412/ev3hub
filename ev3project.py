import json
import os
import time
import sys
import argparse
from operator import methodcaller
from ev3commit import Commit, Changeset
       
class EV3Project(object):
    @classmethod
    def newProject(cls, name, path, ev3data, who, host):
        if os.path.exists(path):
          return None;
        newP = cls(name, path);
        newP.uploadCommit(ev3data, "Initial Commit", who, host);    
        newP.save();
        return newP
     
    def save(self):
        data = {}
        data["head"] = self.head;
        data["failedMerges"] = self.failedMerges;
        data["name"] = self.name;
        with open(self.fullpath("project.json"), "w") as project_file:
            json.dump(data, project_file);      
    
    def addIgnoreComment(self, cid, comment):
        for fm in self.failedMerges:
            if ("{0}".format(fm) == "{0}".format(cid)):
                if not self.failedMerges[fm]:
                    self.failedMerges[fm] = comment;
                    self.save();
                    return ""
                else:
                    return '{0} already had ignore comment'.format(cid)   # this should be impossible...
        return '{0} not in failed merge list'.format(cid)
        
    def fullpath(self, filename):
        return os.path.join(self.path, filename) 
    
    def __init__(self, name, path):
        self.name = name;
        self.path = path
        self.failedMerges = {};
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
        return Commit.from_id(self.path, cid)
        
    def getListOfCommits(self):
        commits = [];
        cid = 1;

        while(os.path.isfile(Commit.file_from_id(self.path, cid))):
            commits.append(Commit.from_id(self.path, cid))
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

        return Commit.from_id(self.path, commit_id).get_ev3_data(self.name)
        
    def uploadCommit(self, ev3data, comment, who, host):
        cid = self.findNextCommit();
        commit = Commit.from_ev3file(self.path, cid, ev3data, comment, who, host, self.name);
        return cid;

    def find_common_parent(self, commit1, commit2):
        parents1 = ["{0}".format(commit1.cid())]
        parents2 = ["{0}".format(commit2.cid())]
        
        while not set(parents1) & set(parents2):
#            print "{0}:{1} - {2}.{3}".format(parents1, parents2,commit1.cid(),commit2.cid())
            if(commit1.parent()):
                commit1 = Commit.from_id(self.path, commit1.parent())
                parents1.append("{0}".format(commit1.cid()))
            if(commit2.parent()):
                commit2 = Commit.from_id(self.path, commit2.parent())
                parents2.append("{0}".format(commit2.cid())) 
            elif commit1.parent() == commit2.parent():   # in this case they are both 0
                parents1.append("0");
                parents2.append("0");
        return (set(parents1) & set(parents2)).pop()   
    
    def remove_failed_merges(self, commit):
        print "In remove failed merge"
        commit = Commit.from_id(self.path, commit.parent());
        while commit and commit.parent():
            foundList = [];
            for fm in self.failedMerges:
                print "FM-{0},{1}".format(fm, commit.cid())
                if ("{0}".format(fm) == "{0}".format(commit.cid())):
                    print " wow"
                    foundList.append(fm)
            if foundList:
                for fm in foundList:
                    self.failedMerges.pop(fm, None)
                commit = Commit.from_id(self.path, commit.parent());
            else:
                return  # Can return because if none were found, none will be found for parents either....
    def merge(self, cid):
        data = {};
        errors = [];
        
        if not self.head:
            self.head = cid;
        else:    
            head_commit = Commit.from_id(self.path, self.head)
            id_commit = Commit.from_id(self.path, cid)
            # find common parent
            parent_cid = self.find_common_parent(head_commit, id_commit)
            if parent_cid == self.head:   # No merging, direct from head
                self.head = cid;
            else:                
                parent_commit = Commit.from_id(self.path, parent_cid)
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
                    self.remove_failed_merges(id_commit);
                    new_id = self.findNextCommit();
                    new_commit = Commit.from_merge(self.path, self.head, new_id, cid, proposed_head_commit.files())
                    cs = Changeset(new_commit, id_commit)             
                    if cs.different():
                        new_commit.save()
                        data["head"] = new_id;
                        self.head = new_id;
                    else:
                        # Throw away new commit
                        data["head"] = cid;
                        self.head = cid;
                else:
                    self.failedMerges[cid] = ""
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
    
    ev3P = EV3Project("test", "testDir")
    cid = ev3P.uploadCommit(ev3contents, "comment", "author", "honeycrisp")
    
    merge_errors = ev3P.merge(cid)
    if merge_errors:
       print merge_errors
    else:
       print "Successful merge!"    
    
    with open("out.zip", "w") as outfile:
       outfile.write(ev3P.download(ev3P.head))