import json

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
    def __init__(self, id, commits):
      self.id = id;
      self.commitDetails = commits[id];
      
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


if __name__ == "__main__":
    with open('testData.json', 'r') as testDataFile:
        testData = json.loads(testDataFile.read())
        oldCommit = commit("1", testData["commits"]);
        newCommit = commit("2", testData["commits"]);
        
        cs = changeset(oldCommit, newCommit);        
        print cs;
      
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
            
                            
                
       