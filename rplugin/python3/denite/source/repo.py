import os
import re
import subprocess
from denite.base.source import Base
from denite.util import debug, error

class Source(Base):

    hightlightGroups = [
        {'name': 'currentBranch', 'link': 'Function',
            'pattern': r'>\zs[a-zA-Z0-9\-_\.]\+\ze', 'parent': 'branch'},
        {'name': 'dirtyCurrentBranch', 'link': 'Exception',
            'pattern': r'>\zs[a-zA-Z0-9\-_\.]\+\ze±', 'parent': 'branch'},
        {'name': 'ahead', 'link': 'String', 'pattern': r'ahead \zs[0-9]\+\ze', 'parent': 'branch'},
        {'name': 'behind', 'link': 'Label', 'pattern': r'behind \zs[0-9]\+\ze', 'parent': 'branch'},
        {'name': 'detached', 'link': 'Exception', 'pattern': r'detached', 'parent': 'branch'},
        {'name': 'repo', 'link': 'Operator', 'pattern': r'\zs[a-zA-Z0-9_\-]\+\ze\s\?', 'next': 'action'},
        {'name': 'action', 'link': 'Identifier', 'pattern': r'.\+$'},
        {'name': 'status', 'link': 'Constant', 'parent': 'action', 'pattern': r': \zs.\+$'},
        {'name': 'statusFailed', 'link': 'Exception', 'parent': 'status', 'pattern': r'Failed'},
        {'name': 'statusSuccess', 'link': 'String', 'parent': 'status', 'pattern': r'Success'},
    ]

    def __init__(self, vim):
        super().__init__(vim)

        self.kind = 'gitrepo'
        self.name = 'git/repo'
        self.matchers = [ 'matcher/regexp' ]
        self.repos = []

    def define_syntax(self):
        self.vim.command(f"syntax region {self.syntax_name}_branch start=/^../hs=e end=/: / " +
                f"containedin={self.syntax_name} " +
                f"contains=deniteConcealedMark nextgroup={self.syntax_name}_repo")
        self.vim.command(f"highlight default link {self.syntax_name}_branch Comment")
        self.vim.command('syntax match deniteSelectedLine /^[*].*/' +
                           ' contains=deniteConcealedMark')
        for syntax in self.hightlightGroups:
            self.vim.command(
                'syntax match {0}_{1} /{2}/ contained containedin={3} {4}'.format(
                    self.syntax_name, syntax['name'], syntax['pattern'],
                    self.syntax_name + ('_' + syntax['parent'] if 'parent' in syntax else ''),
                    'nextgroup=' + self.syntax_name + '_' + syntax['next'] if 'next' in syntax else ''
                )
            )
            self.vim.command(
                'highlight default link {}_{} {}'.format(
                    self.syntax_name, syntax['name'], syntax['link']))

    def on_init(self, context):
        argCount = len(context['args'])
        finder = RepoFinder(self.vim, context['args'][0] if argCount > 0 else '')

        self.repos = finder.find(context['args'][1] if argCount > 1 else 5)
        for repo in self.repos:
            repo.refreshStatus()

    def gather_candidates(self, context):
        candidates = []

        for repo in self.repos:
            candidates.append(self._convert(repo))

        return candidates

    def _convert(self, repo):
        return {
                'action__repo': repo,
                'word': repo.name,
                'abbr': '{}{}{}{}{}: {} {}'.format(
                        repo.branch,
                        '±' if repo.isDirty else '',
                        '+' if repo.hasStash else '',
                        '*' if repo.hasUntracked else '',
                        ' ' + repo.branchInfo if len(repo.branchInfo) else '',
                        repo.name,
                        repo.actionInfo
                    )
                }

class RepoFinder():
    def __init__(self, vim, folder):
        self.folder = folder if os.path.isabs(folder) else os.path.join(vim.call('getcwd'), folder)
        self.repos = []
        self.vim = vim

    def find(self, depth):
        self._find(self.folder, 0, depth)

        return self.repos

    def _find(self, folder, currentDepth, maxDepth):
        if self._isGitRepo(folder):
            self.repos.append(Repo(folder, self.vim))
            return

        if maxDepth is not -1 and currentDepth > maxDepth:
            return

        with os.scandir(folder) as it:
            for entry in os.scandir(folder):
                if not entry.is_dir():
                    continue

                self._find(entry.path, currentDepth + 1, maxDepth)
            it.close()

    def _isGitRepo(self, folder):
        return os.path.isdir(os.path.join(folder, '.git'))

class Repo():
    def __init__(self, folder, vim):
        self.vim = vim
        self.path = os.path.normpath(folder)
        self.name = os.path.basename(self.path)
        self.logs = []
        self.branch = ''
        self.branchInfo = ''
        self.actionInfo = ''
        self.isDirty = False
        self.hasStash = False
        self.hasUntracked = False

    def refreshStatus(self):
        self.branch = ''
        self.branchInfo = ''
        self.isDirty = False
        self.hasStash = False
        self.hasUntracked = False

        self._runStatus()

        result = self._runGit(['stash', 'list'])
        self.hasStash = len(result['stdout']) > 0

    def _runStatus(self):
        result = self._runGit(['status', '--porcelain', '--branch'])
        if result['exitCode']:
            self.branch = '>UNKOWN'
            return

        branchLine = result['stdout'][0][3:].split(' ')
        branch = branchLine.pop(0).split('...')
        if len(branch) is 1:
            self.branch = '>' + branch[0]
        else:
            branch.reverse()
            self.branch = '<->'.join(branch)

        self.branchInfo = ' '.join(branchLine)

        for line in result['stdout'][1:]:
            if len(line) < 1:
                continue

            if line[0] is '?':
                self.hasUntracked = True
            else:
                self.isDirty = True

    def _runGit(self, args):
        command = ['git', '-C', self.path]

        process = subprocess.Popen(command + args, \
                stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE, \
                universal_newlines=True)

        stdout, stderr = process.communicate()

        stdout = str(stdout).split('\n')
        if stdout[-1] is '':
            stdout.pop()

        stderr = str(stderr).split('\n')
        if stderr[-1] is '':
            stderr.pop()

        if process.returncode:
            self.logs.append('----- command: '+ (' '.join(command + args)))
            if len(stdout):
                self.logs.append('stdout:')
                self.logs.extend(stdout)
            if len(stderr):
                self.logs.append('stderr:')
                self.logs.extend(stderr)

        return {
            'exitCode': process.returncode,
            'stdout': stdout,
            'stderr': stderr,
            }

    def getBranches(self):
        result = self._runGit(['branch', '--list', '--no-color'])
        branches = []
        for line in result['stdout']:
            branch = re.search(r'\s([\w\-\.]+)', line)
            if branch:
                branches.append(branch.group(1))

        return branches
