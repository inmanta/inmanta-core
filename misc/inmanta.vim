" Inmanta syntax file
" Filename:     inmanta.vim
" Language:     Inmanta configuration moddeling language
" Maintainer:   Bart Vanbrabant <bart.vanbrabant@inmanta.com>
" URL:
" Last Change:
" Version:
"

if exists("b:current_syntax")
    finish
endif

syn region Comment start="#" end="$" contains=Todo
syn region String start="\"" skip="\\\"" end="\""
syn region String start="\"\"\"" end="\"\"\""
syn region regex start="/" skip="\\/" end="/"
syn match number "\<[0123456789]*\>'\@!"

" Constant
syn keyword Constant null
syn keyword Boolean true false

" Identifier
syn keyword Identifier self

" Statement
syn keyword Conditional if else when elif
syn keyword Repeat for
syn keyword Operator in not or and matching is defined
syn keyword Keyword entity implementation end using implement extends as index parents

" PreProc
syn keyword PreProc import

" Type
syn keyword Type string number int bool list dict
syn keyword Typedef typedef

" Todo
syn keyword Todo contained TODO

"syn match impInstance "\%(\%(def\s\|class\s\|@\)\s*\)\@<=\h\%(\w\|\.\)*" contained

"syntax region Function start="(" end=")"

"highlight link cfComment Comment

hi def link regex String

let b:current_syntax = "inmanta"
