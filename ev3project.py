import json
import zipfile
import cStringIO
import hashlib
import os
import time

# commits json
'''
{
    "commits" : { 1 : {
        "parent" : 0,
        "time" : time,
        "name" : name,
        "host" : host,
        "comment" : comment,
        "files" : {"beep.ev3p" : "FCAD"}}
    }
}
'''

class commit(object):
    def __init__(self, id, commitDetails):
      self.id = id;
      self.commitDetails = commitDetails;
      
    def files(self):
      return self.commitDetails["files"];  
    def __str__(self):
      return "{0}:{1}".format(self.id, self.commitDetails)
        

class changeset(object):
    def __str__(self):
      return "Removed: {0}\nNew: {1}\nModified: {2}\n".format(self.removedFiles, self.newFiles, self.modifiedFiles)
    
    def __init__(self, oldCommit, newCommit):
        self.removedFiles = [];
        self.newFiles = [];
        self.modifiedFiles = [];
        
        oldCommitFiles = oldCommit.files();
        newCommitFiles = newCommit.files();
        
        for newF in newCommitFiles:
           if newF in oldCommitFiles:
               if(newCommitFiles[newF] != oldCommitFiles[newF]):
                   self.modifiedFiles.append(newF);
           else:
              self.newFiles.append(newF);    
        
        for oldF in oldCommitFiles:
            if oldF not in newCommitFiles:
                self.removedFiles.append(oldF);     

    def removedFiles(self):
        return self.removedFiles;
    def newFiles(self):
        return self.newFiles;
    def modifiedFiles(self):
        return self.modifiedFiles;        

    def fileChanged(self,fileName):import json
import zipfile
import cStringIO
import hashlib

# commits json
'''
{
    "commits" : { 1 : {
        "parent" : 0,
        "time" : time,
        "name" : name,
        "host" : host,
        "comment" : comment,
        "files" : {"beep.ev3p" : "FCAD"}}
    }
}
'''

class commit(object):
    def __init__(self, id, commitDetails):
      self.id = id;
      self.commitDetails = commitDetails;
      
    def files(self):
      return self.commitDetails["files"];  
    def __str__(self):
      return "{0}:{1}".format(self.id, self.commitDetails)
        

class changeset(object):
    def __str__(self):
      return "Removed: {0}\nNew: {1}\nModified: {2}\n".format(self.removedFiles, self.newFiles, self.modifiedFiles)
    
    def __init__(self, oldCommit, newCommit):
        self.removedFiles = [];
        self.newFiles = [];
        self.modifiedFiles = [];
        
        oldCommitFiles = oldCommit.files();
        newCommitFiles = newCommit.files();
        
        for newF in newCommitFiles:
           if newF in oldCommitFiles:
               if(newCommitFiles[newF] != oldCommitFiles[newF]):
                   self.modifiedFiles.append(newF);
           else:
              self.newFiles.append(newF);    
        
        for oldF in oldCommitFiles:
            if oldF not in newCommitFiles:
                self.removedFiles.append(oldF);     

    def removedFiles(self):
        return self.removedFiles;
    def newFiles(self):
        return self.newFiles;
    def modifiedFiles(self):
        return self.modifiedFiles;        

    def fileChanged(self,fileName):
        if fileName in self.removedFiles:
            return True;
        if fileName in self.newFiles:
            return True;
        if fileName in self.modifiedFiles:
            return True;
        return False;

class EV3Project(object):
    def __init__(self, name):
        self.name = name;
    def findNextCommit(self):
        id = 1;
        while(os.path.isfile("{0}.json".format(id))):
           id = id + 1;
        return id;  
        
    def uploadCommit(self, ev3data, comment, who, host):
        files = [];
        parent = 0;

        in_memory_zip = cStringIO.StringIO(ev3data)
        with zipfile.ZipFile(in_memory_zip, "r", zipfile.ZIP_DEFLATED, False) as zf:
            for fileName in zf.namelist():
                if fileName == "parent.id":
                    pass
                    # code for putting in parent goes here
                elif fileName == "Project.lvpojx":
                    pass
                    # code for reading variables goes here
                else:  
                    contents = zf.read(fileName)
                    m = hashlib.sha1()
                    m.update(contents)
                    files.append([fileName, m.hexdigest()])
                    if not os.path.isfile("repo/"+m.hexdigest()):
                        zf.extract(fileName, "repo/")
                        os.rename("repo/"+fileName,"repo/"+m.hexdigest())
        commit = {"parent" : parent, "time" : time.time(), "name" : who, "host" : host, "comment" : comment, "files" : files}
        
        id = self.findNextCommit();
        with open("{0}.json".format(id), "w") as outfile:
            json.dump(commit, outfile, indent=4, sort_keys=True, separators=(',', ':'))        
        
if __name__ == "__main__":
    with open("test.ev3", 'r') as ev3File:
        ev3contents = ev3File.read()
    ev3P = EV3Project("test")
    ev3P.uploadCommit(ev3contents, "Initial Commit", "author", "honeycrisp")
        
'''    
    with open('testData.json', 'r') as testDataFile:
        testData = json.loads(testDataFile.read())
        oldCommit = commit("1", testData["commits"]["1"]);
        newCommit = commit("2", testData["commits"]["2"]);
        
        cs = changeset(oldCommit, newCommit);        
        print cs;
'''
              
'''        
class EV3Project(object):
    def __init__(self, name):
        self.name = name;
    

class User(object):
    def __init__(self, login):
        self.name = login;
        self.projects = [];  # this should get list of projects
    def projects(self):
        return self.projects;
'''