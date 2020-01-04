import os
import re
from denite.base.kind import Base
from denite.util import debug, error

class Kind(Base):
    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'gitrepo'
        self.default_action = 'open'
        self.persist_actions = [
                'open', 'status', 'history',
                'git', 'fetch', 'rebase', 'show_log',
                'push', 'stash', 'stash_pop',
                'checkout', 'checkout_smart_b', 'fetch_rebase',
                'git_show_output',
            ]
        self.redraw_actions = [
                'git', 'fetch', 'rebase',
                'push', 'stash', 'stash_pop',
                'checkout', 'checkout_smart_b', 'fetch_rebase',
                'git_show_output',
            ]

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

    def action_git_show_output(self, context):
        command = self.vim.call('input', 'git! ')

        for target in context['targets']:
            repo = target['action__repo']
            repoAction = RepoAction(repo, self.vim)
            result = repoAction.runGit(command)

            self.vim.out_write(' \n')
            self.vim.out_write(repo.path + ':\n')
            if len(result['stdout']):
                self.vim.out_write('  stdout:\n')
                self.vim.out_write('    ')
                self.vim.out_write('\n    '.join(result['stdout']))
                self.vim.out_write(' \n')
            if len(result['stderr']):
                self.vim.out_write('  stderr:\n')
                self.vim.out_write('    ')
                self.vim.out_write('\n    '.join(result['stderr']))
                self.vim.out_write(' \n')

    def action_show_log(self, context):
        for target in context['targets']:
            self.vim.out_write('\n'.join(target['action__repo'].logs))

    def action_fetch(self, context):
        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.fetch()

    def action_rebase(self, context):
        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.rebase()

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

        branch = self._inputBranch(mostBranches)
        if not branch:
            return

        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.checkout(branch)

    def _inputBranch(self, branches):
        branches.sort()
        self.vim.call('denite_git_repo#setBranches', branches)

        return self.vim.call('input', 'Branch: ', '',
                'customlist,denite_git_repo#autocompleteBranches')

    def action_checkout_smart_b(self, context):
        branches = []
        branchesInRepo = {}
        for target in context['targets']:
            repo = target['action__repo']
            branchesInRepo[repo.name] = repo.getBranches()
            for branch in branchesInRepo[repo.name]:
                if branch not in branches:
                    branches.append(branch)

        branch = self._inputBranch(branches)
        if not branch:
            return

        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            if branch in branchesInRepo[repoAction.repo.name]:
                repoAction.checkout(branch)
            else:
                repoAction.checkoutB(branch)

    def action_fetch_rebase(self, context):
        for target in context['targets']:
            repoAction = RepoAction(target['action__repo'], self.vim)
            repoAction.fetchRebase()

class RepoAction():
    def __init__(self, repo, vim):
        self.vim = vim
        self.repo = repo

    def runGit(self, command):
        self.repo.actionInfo = f"Git: {command} "
        return self._runSimpleCommand(command.split(' '))

    def _runSimpleCommand(self, command):
        result = self.repo._runGit(command)

        if result['exitCode']:
            self.repo.actionInfo += 'Failed'
            return

        self.repo.actionInfo += 'Success'
        self.repo.refreshStatus()

        return result

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
        self.repo.actionInfo = 'Rebase: '
        self._runSimpleCommand(['rebase'])

    def push(self):
        self.repo.actionInfo = 'Push: '
        self._runSimpleCommand(['push'])

    def stash(self):
        self.repo.actionInfo = 'Stash: '
        self._runSimpleCommand(['stash'])

    def stashPop(self):
        self.repo.actionInfo = 'Stash pop: '
        self._runSimpleCommand(['stash', 'pop'])

    def checkout(self, branch):
        self.repo.actionInfo = 'Checkout: '
        self._runSimpleCommand(['checkout', branch])

    def checkoutB(self, branch):
        self.repo.actionInfo = 'CheckoutB: '
        self._runSimpleCommand(['checkout', '-b', branch])

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
