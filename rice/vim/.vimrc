" 基础设置
set nocompatible
set number               " 显示行号
set relativenumber       " 相对行号
set autoindent
set smartindent
set tabstop=4
set shiftwidth=4
set expandtab
set nowrap
set ignorecase
set smartcase
set incsearch
set hlsearch
set mouse=a
set undofile
set undolevels=1000
set undoreload=10000

" Leader 键设为 Space（Vim 原生支持）
let mapleader=" "

" 保存与退出
nnoremap <C-s> :w<CR>
nnoremap <leader>qq :wq<CR>

"复制粘贴
xnoremap <silent> y :silent w !wl-copy<CR><CR>
nmap p :r !wl-paste<CR>
nnoremap <silent> yy :silent .w !wl-copy<CR>

" 取消高亮
nnoremap \ :nohlsearch<CR>

" 快速移动
nnoremap <C-j> 5j
nnoremap <C-k> 5k

" 分屏管理
nnoremap <leader>wv :vsplit<CR>
nnoremap <leader>wh :split<CR>
nnoremap <leader>w= <C-w>=
nnoremap <leader>wd :close<CR>

" 窗口切换（emacs 风格）
nnoremap <S-h> <C-w>h
nnoremap <S-l> <C-w>l
nnoremap <S-k> <C-w>k
nnoremap <S-j> <C-w>j

" 启用终端下光标形状切换
if &term =~ "xterm\\|kitty\\|alacritty\\|tmux\\|wezterm"
  let &t_SI = "\e[6 q"   " 插入模式：竖线
  let &t_EI = "\e[2 q"   " 退出插入模式：方块
  let &t_SR = "\e[4 q"   " 替换模式：下划线（可选）
endif

" 简化命令模式移动（光标移动）
cnoremap <C-a> <Home>
cnoremap <C-e> <End>
cnoremap <C-b> <Left>
cnoremap <C-f> <Right>

"终端
nnoremap <C-/> :terminal<CR>

" 语法高亮
syntax on
filetype plugin indent on
