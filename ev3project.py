"""Encapsulates EV3Projects"""

import json
import os
import argparse
import collections
from operator import methodcaller
from ev3commit import Commit, Changeset


class EV3Project(object):
    @classmethod
    def newProject(cls, name, path, ev3data, who, host):
        if os.path.exists(path):
            return None
        newP = cls(name, path)
        newP.uploadCommit(ev3data, "Initial Commit", who, host)
        newP.save()
        return newP

    def save(self):
        data = {}
        data["head"] = self.head
        data["failedMerges"] = self.failedMerges
        data["tags"] = self.tags
        data["name"] = self.name
        with open(self.fullpath("project.json"), "w") as project_file:
            json.dump(data, project_file)

    def addIgnoreComment(self, cid, comment):
        for fm in self.failedMerges:
            if "{0}".format(fm) == "{0}".format(cid):
                if not self.failedMerges[fm]:
                    self.failedMerges[fm] = comment
                    self.save()
                    return ""
                else:
                    # this should be impossible...
                    return '{0} already had ignore comment'.format(cid)
        return '{0} not in failed merge list'.format(cid)

    def addTag(self, cid, description):
        clean = description.strip()
        if not clean:
            return 'tags must not be empty'
        for tag in self.tags:
            if tag == clean:
                return tag + ' already assigned'
        self.tags[description] = cid
        self.save()
        return ''

    def removeTag(self, description):
        clean = description.strip()
        for tag in self.tags:
            if tag == clean:
                del self.tags[tag]
                self.save()
                return ''
        return clean + ' not found'

    def fromTag(self, description):
        clean = description.strip()
        for tag in self.tags:
            if tag == clean:
                return self.getCommit(self.tags[tag])
        return None

    def listTags(self):
        return collections.OrderedDict(sorted(
            list(self.tags.items()), key=lambda t: t[1], reverse=True))

    def fullpath(self, filename):
        return os.path.join(self.path, filename)

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.failedMerges = {}
        self.tags = {}
        self.head = 1

        if not os.path.exists(self.path):
            os.makedirs(self.path)
            os.makedirs(self.fullpath('repo'))

        try:
            with open(self.fullpath("project.json"), "r") as project_file:
                data = json.loads(project_file.read())
                self.head = data["head"]
                self.failedMerges = data["failedMerges"]
                if self.failedMerges is None:
                    self.failedMerges = []
                try:
                    self.tags = data["tags"]
                except KeyError:
                    self.tags = {}
        except IOError:
            pass

    def getCommit(self, cid):
        return Commit.from_id(self.path, cid)

    def getListOfCommits(self):
        commits = []
        cid = 1

        while os.path.isfile(Commit.file_from_id(self.path, cid)):
            commits.append(Commit.from_id(self.path, cid))
            cid = cid + 1
        return sorted(commits, key=methodcaller('time'), reverse=True)

    def findNextCommit(self):
        cid = 1
        while os.path.isfile(Commit.file_from_id(self.path, cid)):
            cid = cid + 1
        return str(cid)

    def download(self, cid):
        commit_id = cid
        if cid == "head":
            commit_id = self.head

        return Commit.from_id(self.path, commit_id).get_ev3_data(self.name)

    def graph(self, cid, showTest):
        commit_id = cid
        if cid == "head":
            commit_id = self.head

        return Commit.from_id(self.path, commit_id).graph(showTest)

    def getDetails(self, cid):
        main_commit = Commit.from_id(self.path, cid)
        commits = self.getListOfCommits()
        fileDetails = {}
        for f in main_commit.files():
            # we want to go backwards and find the first instance of each file
            for commit in reversed(commits):
                if commit.getSHA(f) == main_commit.getSHA(f):
                    fileDetails[f] = commit
                    break
        return fileDetails

    def uploadCommit(self, ev3data, comment, who, host):
        cid = self.findNextCommit()
        commit = Commit.from_ev3file(
            self.path, cid, ev3data, comment, who, host, self.name)
        head = Commit.from_id(self.path, self.head)
        cs = Changeset(commit, head)
        if (not cs.different()) and (cid != "1"):
            commit.delete()
            return 0
        return cid

    def find_common_parent(self, commit1, commit2):
        parents1 = ["{0}".format(commit1.cid())]
        parents2 = ["{0}".format(commit2.cid())]

        while not set(parents1) & set(parents2):
            if commit1.parent():
                commit1 = Commit.from_id(self.path, commit1.parent())
                parents1.append("{0}".format(commit1.cid()))
            if commit2.parent():
                commit2 = Commit.from_id(self.path, commit2.parent())
                parents2.append("{0}".format(commit2.cid()))
            elif commit1.parent() == commit2.parent():   # in this case they are both 0
                parents1.append("0")
                parents2.append("0")
        return (set(parents1) & set(parents2)).pop()

    def remove_failed_merges(self, commit):
        while commit and commit.parent():
            foundList = []
            for fm in self.failedMerges:
                print("FM-{0},{1}".format(fm, commit.cid()))
                if "{0}".format(fm) == "{0}".format(commit.cid()):
                    print(" wow")
                    foundList.append(fm)
            if foundList:
                for fm in foundList:
                    self.failedMerges.pop(fm, None)
                commit = Commit.from_id(self.path, commit.parent())
            else:
                # Can return because if none were found, none will be found for parents either....
                return

    def try_merge(self, id_commit):
        errors_added = []
        errors_modified = []

        head_commit = Commit.from_id(self.path, self.head)
        # find common parent
        parent_cid = self.find_common_parent(head_commit, id_commit)

        parent_commit = Commit.from_id(self.path, parent_cid)
        changes_to_head = Changeset(parent_commit, head_commit)
        changes_to_commit = Changeset(parent_commit, id_commit)
        proposed_head_commit = head_commit

        for filename in changes_to_commit.newFiles():
            if (filename in changes_to_head.newFiles()) and (
                    head_commit.getSHA(filename) != id_commit.getSHA(filename)):
                errors_added.append(filename)
            else:
                proposed_head_commit.files()[filename] = id_commit.files()[
                    filename]
        for filename in changes_to_commit.modifiedFiles():
            if (filename in changes_to_head.modifiedFiles()) and (
                    head_commit.getSHA(filename) != id_commit.getSHA(filename)):
                errors_modified.append(filename)
            else:
                proposed_head_commit.files()[filename] = id_commit.files()[
                    filename]
        for filename in changes_to_commit.removedFiles():
            if filename not in changes_to_head.modifiedFiles():
                proposed_head_commit.remove_file(filename)

        return (proposed_head_commit, errors_added, errors_modified)

    def manual_merge(self, cid, commit_files, head_files):
        errors = []
        id_commit = Commit.from_id(self.path, cid)
        (proposed_head_commit, errors_added,
         errors_modified) = self.try_merge(id_commit)
        conflicts = errors_added + errors_modified
        for conflict in conflicts:
            if conflict in commit_files:
                proposed_head_commit.files()[conflict] = id_commit.files()[
                    conflict]
            elif conflict in head_files:
                pass
            else:
                errors.append(conflict)
        if not errors:
            self.remove_failed_merges(id_commit)
            new_id = self.findNextCommit()
            new_commit = Commit.from_manual_merge(
                self.path, self.head, new_id, cid, proposed_head_commit.files())
            new_commit.save()
            self.head = new_id
        else:
            self.failedMerges[cid] = ""

        data = {}
        data["head"] = self.head
        data["failedMerges"] = self.failedMerges
        with open(self.fullpath("project.json"), "w") as project_file:
            json.dump(data, project_file)

        return errors

    def merge(self, cid):
        errors = []
        if not self.head:
            self.head = cid
        else:
            id_commit = Commit.from_id(self.path, cid)
            if id_commit.parent() == self.head:
                self.head = cid
            else:
                (proposed_head_commit, errors_added,
                 errors_modified) = self.try_merge(id_commit)
                for filename in errors_added:
                    errors.append("{0} added in both".format(filename))
                for filename in errors_modified:
                    errors.append("{0} modified in both".format(filename))

                print("Errors: {0}".format(errors))

                if not errors:
                    self.remove_failed_merges(id_commit)
                    new_id = self.findNextCommit()
                    new_commit = Commit.from_merge(
                        self.path, self.head, new_id, cid, proposed_head_commit.files())
                    cs = Changeset(new_commit, id_commit)
                    if cs.different():
                        new_commit.save()
                        self.head = new_id
                    else:
                        # No need for merge commit
                        self.head = cid
                else:
                    self.failedMerges[cid] = ""
        data = {}
        data["head"] = self.head
        data["failedMerges"] = self.failedMerges
        with open(self.fullpath("project.json"), "w") as project_file:
            json.dump(data, project_file)

        return errors


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Test ev3project code")
    parser.add_argument('file')
    parser.add_argument('-c', "--comment", help="comment for checkin")
    args = parser.parse_args()

    commit_filename = args.file
    with open(commit_filename, 'r') as ev3File:
        ev3contents = ev3File.read()

    ev3P = EV3Project("test", "testDir")
    commitId = ev3P.uploadCommit(
        ev3contents, "comment", "author", "honeycrisp")

    merge_errors = ev3P.merge(commitId)
    if merge_errors:
        print(merge_errors)
    else:
        print("Successful merge!")

    with open("out.zip", "w") as outfile:
        outfile.write(ev3P.download(ev3P.head))
