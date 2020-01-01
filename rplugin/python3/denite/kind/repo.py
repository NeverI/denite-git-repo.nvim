import os
import re
from denite.base.kind import Base
from denite.util import debug, error

class Kind(Base):
    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'gitrepo'
        self.default_action = 'open'
        self.persist_actions = [ 'open', 'fetch', 'rebase', 'show_log', 'push', 'stash', 'stash_pop' ]
        self.redraw_actions = [ 'fetch', 'rebase', 'push', 'stash', 'stash_pop' ]

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

    def action_rebase(self, context):
        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.rebase()

    def action_show_log(self, context):
        for target in context['targets']:
            debug(self.vim, '\n'.join(target['action__repo'].logs))

    def action_push(self, context):
        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.push()

    def action_stash(self, context):
        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.stash()

    def action_stash_pop(self, context):
        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.stashPop()

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
        self.repo.refreshStatus()

    def rebase(self):
        result = self.repo._runGit(['rebase'])
        self.repo.refreshStatus()
        self.repo.actionInfo = 'Rebase: '

        if result['exitCode']:
            self.repo.actionInfo += 'Failed'
            return

        self.repo.actionInfo += 'Success'

    def push(self):
        result = self.repo._runGit(['push'])
        self.repo.actionInfo = 'Push: '

        if result['exitCode']:
            self.repo.actionInfo += 'Failed'
            return

        self.repo.actionInfo += 'Success'
        self.repo.refreshStatus()

    def stash(self):
        result = self.repo._runGit(['stash'])
        self.repo.actionInfo = 'Stash: '

        if result['exitCode']:
            self.repo.actionInfo += 'Failed'
            return

        self.repo.actionInfo += 'Success'
        self.repo.refreshStatus()

    def stashPop(self):
        result = self.repo._runGit(['stash', 'pop'])
        self.repo.actionInfo = 'Stash pop: '

        if result['exitCode']:
            self.repo.actionInfo += 'Failed'
            return

        self.repo.actionInfo += 'Success'
        self.repo.refreshStatus()
