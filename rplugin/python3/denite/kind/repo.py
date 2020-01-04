import os
import re
from denite.base.kind import Base
from denite.util import debug, error

class Kind(Base):
    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'gitrepo'
        self.default_action = 'open'
        self.persist_actions = [ 'open', 'status', 'history', 'git', 'fetch', 'rebase', 'show_log', 'push', 'stash', 'stash_pop', 'checkout', 'fetch_rebase' ]
        self.redraw_actions = [ 'git', 'fetch', 'rebase', 'push', 'stash', 'stash_pop', 'checkout', 'fetch_rebase' ]

    def action_open(self, context):
        for target in context['targets']:
            repo = target['action__repo']
            if repo.isDirty or repo.actionInfo.find('Failed') > -1:
                self._runInTab(repo, 'Gstatus')
            else:
                self._runInTab(repo, 'GV')

    def action_status(self, context):
        for target in context['targets']:
            self._runInTab(target['action__repo'], 'Gstatus')

    def _runInTab(self, repo, command):
        self.vim.command('silent tabedit ' + os.path.join(repo.path, 'git_repo'))
        bufvars = self.vim.current.buffer.options
        bufvars['buftype'] = 'nofile'
        bufnr =  self.vim.current.buffer.number
        self.vim.command('silent lcd ' + repo.path)
        self.vim.command(command)
        self.vim.command(f"bdelete {bufnr}")

    def action_history(self, context):
        for target in context['targets']:
            self._runInTab(target['action__repo'], 'GV')

    def action_git(self, context):
        command = self.vim.call('input', 'git ')

        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.runGit(command)

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

    def action_checkout(self, context):
        branches = {}
        mostBranches = []
        for target in context['targets']:
            repo = target['action__repo']
            branchesInRepo = repo.getBranches()
            branches[repo.name] = branchesInRepo
            if len(branchesInRepo) > len(mostBranches):
                mostBranches = branchesInRepo

        for repoName in branches:
            for branch in mostBranches.copy():
                if branch not in branches[repoName]:
                    mostBranches.remove(branch)

        mostBranches.sort()
        self.vim.call('denite_git_repo#setBranches', mostBranches)
        branch = self.vim.call('input', 'Branch: ', '',
                'customlist,denite_git_repo#autocompleteBranches')

        if not branch:
            return

        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.checkout(branch)

    def action_fetch_rebase(self, context):
        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.fetchRebase()

class RepoAction():
    def __init__(self, repo, vim):
        self.vim = vim
        self.repo = repo

    def runGit(self, command):
        result = self.repo._runGit(command.split(' '))
        self.repo.actionInfo = f"Git: {command} "

        if result['exitCode']:
            self.repo.actionInfo += 'Failed'
            return

        self.repo.actionInfo += 'Success'
        self.repo.refreshStatus()

    def fetch(self):
        news = self._doFetch()
        self.repo.actionInfo = 'Fetch: '

        if news is None:
            self.repo.actionInfo += 'Failed'
            return

        if len(news) is 0:
            self.repo.actionInfo += 'Nothing new'
            return

        self.repo.actionInfo += ', '.join(news)
        self.repo.refreshStatus()

    def _doFetch(self):
        result = self.repo._runGit(['fetch'])

        if result['exitCode']:
            return None

        if len(result['stderr']) is 0:
            return []

        news = []
        for line in result['stderr']:
            branchMatch = re.search(r'\s([\w\.\-_]+)\s+->', line)
            if not branchMatch:
                continue

            branch = branchMatch.group(1)
            if re.search(r'\s\[new', line):
                branch += '*'

            news.append(branch)

        return news

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

    def checkout(self, branch):
        result = self.repo._runGit(['checkout', branch])
        self.repo.actionInfo = 'Checkout: '

        if result['exitCode']:
            self.repo.actionInfo += 'Failed'
            return

        self.repo.actionInfo += 'Success'
        self.repo.refreshStatus()

    def fetchRebase(self):
        news = self._doFetch()
        self.repo.actionInfo = 'FetchRebase:'

        if news is None:
            self.repo.actionInfo += ' fetch Failed'
            return

        if len(news) is 0:
            self.repo.actionInfo += ' Nothing new'
            return

        if self.repo.isDirty:
            self.repo._runGit(['stash'])
            self.repo.actionInfo += ' stashed;'

        rebaseResult = self.repo._runGit(['rebase'])
        if rebaseResult['exitCode']:
            self.repo.actionInfo += ' rebase Failed'
            self.repo.refreshStatus()
            return

        if self.repo.isDirty:
            stashPopResult = self.repo._runGit(['stash', 'pop'])
            if stashPopResult['exitCode']:
                self.repo.actionInfo = 'FetchRebase: rebase Success; stash pop Failed'
                self.repo.refreshStatus()
                return

        self.repo.actionInfo = 'FetchRebase: ' + ','.join(news) + ' Success'
        self.repo.refreshStatus()
