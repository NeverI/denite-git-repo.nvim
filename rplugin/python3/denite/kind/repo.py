from denite.base.kind import Base
import os
#from denite.source.repo import Repo

class Kind(Base):
    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'gitrepo'
        self.default_action = 'open'
        self.persist_actions = [ 'open' ]
        self.redraw_actions = []

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
