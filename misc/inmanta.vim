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

syn region Comment start="#" end="$"
syn region String start="\"" skip="\\\"" end="\""
syn region String start="\"\"\"" end="\"\"\""
syn region regex start="/" skip="\\/" end="/"
syn match number "\<[0123456789]*\>'\@!"

syn keyword Keyword implementation end using entity when implement extends in not or and as matching index for parents if else is defined
syn keyword PreProc import
syn keyword Typedef typedef
syn keyword Boolean true false
syn keyword Type string number int bool list dict

"syn match impInstance "\%(\%(def\s\|class\s\|@\)\s*\)\@<=\h\%(\w\|\.\)*" contained

"syntax region Function start="(" end=")"

"highlight link cfComment Comment

hi def link regex String

let b:current_syntax = "inmanta"
