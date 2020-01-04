let s:branches = []

function! denite_git_repo#setBranches(branches)
  let s:branches = a:branches
endfunction

function! denite_git_repo#autocompleteBranches(arglead, cmdline, cursorPos)
  return filter(copy(s:branches), "stridx(v:val, a:arglead) == 0")
endfunction
