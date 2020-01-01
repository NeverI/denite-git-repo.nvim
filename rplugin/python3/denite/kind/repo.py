import os
import re
from denite.base.kind import Base
from denite.util import debug, error

class Kind(Base):
    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'gitrepo'
        self.default_action = 'open'
        self.persist_actions = [ 'open', 'fetch' ]
        self.redraw_actions = [ 'fetch']

    def action_open(self, context):
        for target in context['targets']:
            repo = target['action__repo']
            self.vim.command('silent tabedit ' + os.path.join(repo.path, 'git_repo'))
            bufvars = self.vim.current.buffer.options
            bufvars['buftype'] = 'nofile'
            bufnr =  self.vim.current.buffer.number
            self.vim.command('cd ' + repo.path)
            self.vim.command('Gstatus')
            self.vim.command(f"bdelete {bufnr}")

    def action_fetch(self, context):
        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.fetch()

class RepoAction():
    def __init__(self, repo, vim):
        self.vim = vim
        self.repo = repo

    def fetch(self):
        result = self.repo._runGit(['fetch'])
        self.repo.actionInfo = 'Fetch: '

        if result['exitCode']:
            self.repo.actionInfo += 'Failed'
            return

        if len(result['stderr']) is 0:
            self.repo.actionInfo += 'Nothing new'
            return

        news = []
        for line in result['stderr']:
            branchMatch = re.search(r'\s([\w\.\-_]+)\s+->', line)
            if not branchMatch:
                continue

            branch = branchMatch.group(1)
            if re.search(r'\s\[new', line):
                branch += '*'

            news.append(branch)

        self.repo.actionInfo += ', '.join(news)
