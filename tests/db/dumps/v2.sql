--
-- PostgreSQL database dump
--

-- Dumped from database version 11.5
-- Dumped by pg_dump version 11.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
-- SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: change; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.change AS ENUM (
    'nochange',
    'created',
    'purged',
    'updated'
);


--
-- Name: resourceaction_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resourceaction_type AS ENUM (
    'store',
    'push',
    'pull',
    'deploy',
    'dryrun',
    'getfact',
    'other'
);


--
-- Name: resourcestate; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resourcestate AS ENUM (
    'unavailable',
    'skipped',
    'dry',
    'deployed',
    'failed',
    'deploying',
    'available',
    'cancelled',
    'undefined',
    'skipped_for_undefined',
    'processing_events'
);


--
-- Name: versionstate; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.versionstate AS ENUM (
    'success',
    'failed',
    'deploying',
    'pending'
);


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: agent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent (
    environment uuid NOT NULL,
    name character varying NOT NULL,
    last_failover timestamp without time zone,
    paused boolean DEFAULT false,
    id_primary uuid
);


--
-- Name: agentinstance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agentinstance (
    id uuid NOT NULL,
    process uuid NOT NULL,
    name character varying NOT NULL,
    expired timestamp without time zone,
    tid uuid NOT NULL
);


--
-- Name: agentprocess; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agentprocess (
    hostname character varying NOT NULL,
    environment uuid NOT NULL,
    first_seen timestamp without time zone,
    last_seen timestamp without time zone,
    expired timestamp without time zone,
    sid uuid NOT NULL
);


--
-- Name: code; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.code (
    environment uuid NOT NULL,
    resource character varying NOT NULL,
    version integer NOT NULL,
    source_refs jsonb
);


--
-- Name: compile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.compile (
    id uuid NOT NULL,
    environment uuid NOT NULL,
    started timestamp without time zone,
    completed timestamp without time zone,
    requested timestamp without time zone,
    metadata jsonb,
    environment_variables jsonb,
    do_export boolean,
    force_update boolean,
    success boolean,
    version integer,
    remote_id uuid,
    handled boolean
);


--
-- Name: configurationmodel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configurationmodel (
    version integer NOT NULL,
    environment uuid NOT NULL,
    date timestamp without time zone,
    released boolean DEFAULT false,
    deployed boolean DEFAULT false,
    result public.versionstate DEFAULT 'pending'::public.versionstate,
    version_info jsonb,
    total integer DEFAULT 0,
    undeployable character varying[],
    skipped_for_undeployable character varying[]
);


--
-- Name: dryrun; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dryrun (
    id uuid NOT NULL,
    environment uuid NOT NULL,
    model integer NOT NULL,
    date timestamp without time zone,
    total integer DEFAULT 0,
    todo integer DEFAULT 0,
    resources jsonb DEFAULT '{}'::jsonb
);


--
-- Name: environment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environment (
    id uuid NOT NULL,
    name character varying NOT NULL,
    project uuid NOT NULL,
    repo_url character varying DEFAULT ''::character varying,
    repo_branch character varying DEFAULT ''::character varying,
    settings jsonb DEFAULT '{}'::jsonb
);


--
-- Name: form; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.form (
    environment uuid NOT NULL,
    form_type character varying NOT NULL,
    options jsonb,
    fields jsonb,
    defaults jsonb,
    field_options jsonb
);


--
-- Name: formrecord; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.formrecord (
    id uuid NOT NULL,
    form character varying NOT NULL,
    environment uuid NOT NULL,
    fields jsonb,
    changed timestamp without time zone
);


--
-- Name: parameter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parameter (
    id uuid NOT NULL,
    name character varying NOT NULL,
    value character varying DEFAULT ''::character varying NOT NULL,
    environment uuid NOT NULL,
    resource_id character varying DEFAULT ''::character varying,
    source character varying NOT NULL,
    updated timestamp without time zone,
    metadata jsonb
);


--
-- Name: project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project (
    id uuid NOT NULL,
    name character varying NOT NULL
);


--
-- Name: report; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report (
    id uuid NOT NULL,
    started timestamp without time zone NOT NULL,
    completed timestamp without time zone,
    command character varying NOT NULL,
    name character varying NOT NULL,
    errstream character varying DEFAULT ''::character varying,
    outstream character varying DEFAULT ''::character varying,
    returncode integer,
    compile uuid NOT NULL
);


--
-- Name: resource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource (
    environment uuid NOT NULL,
    model integer NOT NULL,
    resource_id character varying NOT NULL,
    resource_version_id character varying NOT NULL,
    agent character varying NOT NULL,
    last_deploy timestamp without time zone,
    attributes jsonb,
    attribute_hash character varying,
    status public.resourcestate DEFAULT 'available'::public.resourcestate,
    provides character varying[] DEFAULT ARRAY[]::character varying[]
);


--
-- Name: resourceaction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resourceaction (
    action_id uuid NOT NULL,
    action public.resourceaction_type NOT NULL,
    started timestamp without time zone NOT NULL,
    finished timestamp without time zone,
    messages jsonb[],
    status public.resourcestate,
    changes jsonb DEFAULT '{}'::jsonb,
    change public.change,
    send_event boolean
);


--
-- Name: resourceversionid; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resourceversionid (
    environment uuid NOT NULL,
    action_id uuid NOT NULL,
    resource_version_id character varying NOT NULL
);


--
-- Name: schemamanager; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schemamanager (
    name character varying NOT NULL,
    current_version integer NOT NULL
);


--
-- Name: unknownparameter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.unknownparameter (
    id uuid NOT NULL,
    name character varying NOT NULL,
    environment uuid NOT NULL,
    source character varying NOT NULL,
    resource_id character varying DEFAULT ''::character varying,
    version integer NOT NULL,
    metadata jsonb,
    resolved boolean DEFAULT false
);


--
-- Data for Name: agent; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent (environment, name, last_failover, paused, id_primary) FROM stdin;
d357482f-11c9-421e-b3c1-36d11ac5b975	localhost	2019-09-27 13:30:46.239275	f	dd2524a7-b737-4b74-a68d-27fe9e4ec7b6
d357482f-11c9-421e-b3c1-36d11ac5b975	internal	2019-09-27 13:30:46.935564	f	5df30799-e712-46a4-9f90-537c5adb47f3
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
5df30799-e712-46a4-9f90-537c5adb47f3	3f72fbb6-e11a-11e9-ab75-48f17fc492fd	internal	\N	d357482f-11c9-421e-b3c1-36d11ac5b975
dd2524a7-b737-4b74-a68d-27fe9e4ec7b6	3f72fbb6-e11a-11e9-ab75-48f17fc492fd	localhost	\N	d357482f-11c9-421e-b3c1-36d11ac5b975
27781229-ff77-47ea-b9fa-34e2fccb4aa5	3d63f366-e11a-11e9-baf5-48f17fc492fd	internal	2019-09-27 13:30:46.923971	d357482f-11c9-421e-b3c1-36d11ac5b975
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
font.ii.inmanta.com	d357482f-11c9-421e-b3c1-36d11ac5b975	2019-09-27 13:30:44.834187	2019-09-27 13:30:44.922685	2019-09-27 13:30:46.923971	3d63f366-e11a-11e9-baf5-48f17fc492fd
font.ii.inmanta.com	d357482f-11c9-421e-b3c1-36d11ac5b975	2019-09-27 13:30:46.226793	2019-09-27 13:30:48.032626	\N	3f72fbb6-e11a-11e9-ab75-48f17fc492fd
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
d357482f-11c9-421e-b3c1-36d11ac5b975	std::Service	1569583841	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::File	1569583841	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::Directory	1569583841	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::Package	1569583841	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::Symlink	1569583841	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::AgentConfig	1569583841	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::Service	1569583847	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::File	1569583847	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::Directory	1569583847	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::Package	1569583847	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::Symlink	1569583847	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
d357482f-11c9-421e-b3c1-36d11ac5b975	std::AgentConfig	1569583847	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmp1xp_gsi7/server/environments/d357482f-11c9-421e-b3c1-36d11ac5b975/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.1"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled) FROM stdin;
08d17124-8cb4-4526-ad63-5af768fc98b7	d357482f-11c9-421e-b3c1-36d11ac5b975	2019-09-27 13:30:37.844022	2019-09-27 13:30:42.042455	2019-09-27 13:30:37.836964	{"type": "api", "message": "Recompile trigger through API call"}	{"_": "/home/wouter/.virtualenvs/inmanta-pg/bin/pytest", "ENV": "/usr/share/Modules/init/profile.sh", "PWD": "/home/wouter/projects/inmanta", "ZSH": "/home/wouter/.oh-my-zsh", "HOME": "/home/wouter", "LANG": "en_US.UTF-8", "LESS": "-R", "MAIL": "/var/spool/mail/wouter", "PATH": "/home/wouter/.virtualenvs/inmanta-pg/bin:/usr/share/Modules/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/home/wouter/bin:/usr/pgsql-10/bin/", "TERM": "xterm-256color", "USER": "wouter", "FPATH": "/home/wouter/.oh-my-zsh/plugins/pip:/home/wouter/.oh-my-zsh/plugins/pep8:/home/wouter/.oh-my-zsh/plugins/npm:/home/wouter/.oh-my-zsh/plugins/httpie:/home/wouter/.oh-my-zsh/plugins/mvn:/home/wouter/.oh-my-zsh/plugins/virtualenv:/home/wouter/.oh-my-zsh/plugins/git:/home/wouter/.oh-my-zsh/functions:/home/wouter/.oh-my-zsh/completions:/usr/share/Modules/init/zsh-functions:/usr/local/share/zsh/site-functions:/usr/share/zsh/site-functions:/usr/share/zsh/5.7.1/functions", "PAGER": "less", "SHELL": "/usr/bin/zsh", "SHLVL": "1", "OLDPWD": "/home/wouter", "DISPLAY": ":0", "KDEDIRS": "/usr", "LOGNAME": "wouter", "MANPATH": ":", "BASH_ENV": "/usr/share/Modules/init/bash", "GDM_LANG": "en_US.UTF-8", "HISTSIZE": "50000", "HOSTNAME": "font.ii.inmanta.com", "LC_CTYPE": "en_US.UTF-8", "LESSOPEN": "||/usr/bin/lesspipe.sh %s", "LSCOLORS": "Gxfxcxdxbxegedabagacad", "USERNAME": "wouter", "XDG_SEAT": "seat0", "XDG_VTNR": "2", "COLORTERM": "truecolor", "LS_COLORS": "rs=0:di=38;5;33:ln=38;5;51:mh=00:pi=40;38;5;11:so=38;5;13:do=38;5;5:bd=48;5;232;38;5;11:cd=48;5;232;38;5;3:or=48;5;232;38;5;9:mi=01;05;37;41:su=48;5;196;38;5;15:sg=48;5;11;38;5;16:ca=48;5;196;38;5;226:tw=48;5;10;38;5;16:ow=48;5;10;38;5;21:st=48;5;21;38;5;15:ex=38;5;40:*.tar=38;5;9:*.tgz=38;5;9:*.arc=38;5;9:*.arj=38;5;9:*.taz=38;5;9:*.lha=38;5;9:*.lz4=38;5;9:*.lzh=38;5;9:*.lzma=38;5;9:*.tlz=38;5;9:*.txz=38;5;9:*.tzo=38;5;9:*.t7z=38;5;9:*.zip=38;5;9:*.z=38;5;9:*.dz=38;5;9:*.gz=38;5;9:*.lrz=38;5;9:*.lz=38;5;9:*.lzo=38;5;9:*.xz=38;5;9:*.zst=38;5;9:*.tzst=38;5;9:*.bz2=38;5;9:*.bz=38;5;9:*.tbz=38;5;9:*.tbz2=38;5;9:*.tz=38;5;9:*.deb=38;5;9:*.rpm=38;5;9:*.jar=38;5;9:*.war=38;5;9:*.ear=38;5;9:*.sar=38;5;9:*.rar=38;5;9:*.alz=38;5;9:*.ace=38;5;9:*.zoo=38;5;9:*.cpio=38;5;9:*.7z=38;5;9:*.rz=38;5;9:*.cab=38;5;9:*.wim=38;5;9:*.swm=38;5;9:*.dwm=38;5;9:*.esd=38;5;9:*.jpg=38;5;13:*.jpeg=38;5;13:*.mjpg=38;5;13:*.mjpeg=38;5;13:*.gif=38;5;13:*.bmp=38;5;13:*.pbm=38;5;13:*.pgm=38;5;13:*.ppm=38;5;13:*.tga=38;5;13:*.xbm=38;5;13:*.xpm=38;5;13:*.tif=38;5;13:*.tiff=38;5;13:*.png=38;5;13:*.svg=38;5;13:*.svgz=38;5;13:*.mng=38;5;13:*.pcx=38;5;13:*.mov=38;5;13:*.mpg=38;5;13:*.mpeg=38;5;13:*.m2v=38;5;13:*.mkv=38;5;13:*.webm=38;5;13:*.ogm=38;5;13:*.mp4=38;5;13:*.m4v=38;5;13:*.mp4v=38;5;13:*.vob=38;5;13:*.qt=38;5;13:*.nuv=38;5;13:*.wmv=38;5;13:*.asf=38;5;13:*.rm=38;5;13:*.rmvb=38;5;13:*.flc=38;5;13:*.avi=38;5;13:*.fli=38;5;13:*.flv=38;5;13:*.gl=38;5;13:*.dl=38;5;13:*.xcf=38;5;13:*.xwd=38;5;13:*.yuv=38;5;13:*.cgm=38;5;13:*.emf=38;5;13:*.ogv=38;5;13:*.ogx=38;5;13:*.aac=38;5;45:*.au=38;5;45:*.flac=38;5;45:*.m4a=38;5;45:*.mid=38;5;45:*.midi=38;5;45:*.mka=38;5;45:*.mp3=38;5;45:*.mpc=38;5;45:*.ogg=38;5;45:*.ra=38;5;45:*.wav=38;5;45:*.oga=38;5;45:*.opus=38;5;45:*.spx=38;5;45:*.xspf=38;5;45:", "GDMSESSION": "gnome-xorg", "MODULEPATH": "/etc/scl/modulefiles:/etc/scl/modulefiles:/usr/share/Modules/modulefiles:/etc/modulefiles:/usr/share/modulefiles", "WINDOWPATH": "2", "XAUTHORITY": "/run/user/1000/gdm/Xauthority", "XMODIFIERS": "@im=ibus", "HISTCONTROL": "ignoredups", "MODULESHOME": "/usr/share/Modules", "MODULES_CMD": "/usr/share/Modules/libexec/modulecmd.tcl", "OS_AUTH_URL": "http://node2.ii.inmanta.com:5000/v3", "OS_PASSWORD": "21ce1521d8d344f3", "OS_USERNAME": "admin", "VIRTUAL_ENV": "/home/wouter/.virtualenvs/inmanta-pg", "VTE_VERSION": "5603", "WORKON_HOME": "/home/wouter/.virtualenvs", "QT_IM_MODULE": "ibus", "GUESTFISH_PS1": "\\\\[\\\\e[1;32m\\\\]><fs>\\\\[\\\\e[0;31m\\\\] ", "LOADEDMODULES": "", "SSH_AGENT_PID": "2255", "SSH_AUTH_SOCK": "/run/user/1000/keyring/ssh", "XDG_DATA_DIRS": "/home/wouter/.local/share/flatpak/exports/share/:/var/lib/flatpak/exports/share/:/usr/local/share/:/usr/share/", "GUESTFISH_INIT": "\\\\e[1;34m", "XDG_SESSION_ID": "2", "DESKTOP_SESSION": "gnome-xorg", "SESSION_MANAGER": "local/unix:@/tmp/.ICE-unix/2211,unix/unix:/tmp/.ICE-unix/2211", "XDG_MENU_PREFIX": "gnome-", "XDG_RUNTIME_DIR": "/run/user/1000", "GUESTFISH_OUTPUT": "\\\\e[0m", "XDG_SESSION_TYPE": "x11", "GUESTFISH_RESTORE": "\\\\e[0m", "XDG_SESSION_CLASS": "user", "MODULEPATH_modshare": "/usr/share/modulefiles:1:/usr/share/Modules/modulefiles:1:/etc/modulefiles:1", "PYTEST_CURRENT_TEST": "tests/db/dump_tool.py::test_dump_db (call)", "XDG_CURRENT_DESKTOP": "GNOME", "XDG_SESSION_DESKTOP": "gnome-xorg", "DESKTOP_AUTOSTART_ID": "10704fa85eea63dd5156957607823724100000022110007", "GNOME_TERMINAL_SCREEN": "/org/gnome/Terminal/screen/b641bf14_5790_4ce2_8b69_ea8a4164c5e9", "GNOME_TERMINAL_SERVICE": ":1.99", "MODULES_RUN_QUARANTINE": "LD_LIBRARY_PATH", "_VIRTUALENVWRAPPER_API": " mkvirtualenv rmvirtualenv lsvirtualenv showvirtualenv workon add2virtualenv cdsitepackages cdvirtualenv lssitepackages toggleglobalsitepackages cpvirtualenv setvirtualenvproject mkproject cdproject mktmpenv wipeenv allvirtualenv mkvirtualenv rmvirtualenv lsvirtualenv showvirtualenv workon add2virtualenv cdsitepackages cdvirtualenv lssitepackages toggleglobalsitepackages cpvirtualenv setvirtualenvproject mkproject cdproject mktmpenv wipeenv allvirtualenv", "OS_IDENTITY_API_VERSION": "3", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus", "VIRTUALENVWRAPPER_SCRIPT": "/usr/bin/virtualenvwrapper.sh", "VIRTUALENVWRAPPER_HOOK_DIR": "/home/wouter/.virtualenvs", "VIRTUAL_ENV_DISABLE_PROMPT": "1", "VIRTUALENVWRAPPER_WORKON_CD": "1", "VIRTUALENVWRAPPER_VIRTUALENV": "/usr/bin/venv", "VIRTUALENVWRAPPER_PROJECT_FILENAME": ".project"}	t	t	t	1569583841	7d4e27b7-6064-4415-bc7d-a9100e08ed75	t
616c9a73-9244-46b2-a77e-1523c2ce5274	d357482f-11c9-421e-b3c1-36d11ac5b975	2019-09-27 13:30:47.162633	2019-09-27 13:30:47.841974	2019-09-27 13:30:47.154453	{"type": "api", "message": "Recompile trigger through API call"}	{"_": "/home/wouter/.virtualenvs/inmanta-pg/bin/pytest", "ENV": "/usr/share/Modules/init/profile.sh", "PWD": "/home/wouter/projects/inmanta", "ZSH": "/home/wouter/.oh-my-zsh", "HOME": "/home/wouter", "LANG": "en_US.UTF-8", "LESS": "-R", "MAIL": "/var/spool/mail/wouter", "PATH": "/home/wouter/.virtualenvs/inmanta-pg/bin:/usr/share/Modules/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/home/wouter/bin:/usr/pgsql-10/bin/", "TERM": "xterm-256color", "USER": "wouter", "FPATH": "/home/wouter/.oh-my-zsh/plugins/pip:/home/wouter/.oh-my-zsh/plugins/pep8:/home/wouter/.oh-my-zsh/plugins/npm:/home/wouter/.oh-my-zsh/plugins/httpie:/home/wouter/.oh-my-zsh/plugins/mvn:/home/wouter/.oh-my-zsh/plugins/virtualenv:/home/wouter/.oh-my-zsh/plugins/git:/home/wouter/.oh-my-zsh/functions:/home/wouter/.oh-my-zsh/completions:/usr/share/Modules/init/zsh-functions:/usr/local/share/zsh/site-functions:/usr/share/zsh/site-functions:/usr/share/zsh/5.7.1/functions", "PAGER": "less", "SHELL": "/usr/bin/zsh", "SHLVL": "1", "OLDPWD": "/home/wouter", "DISPLAY": ":0", "KDEDIRS": "/usr", "LOGNAME": "wouter", "MANPATH": ":", "BASH_ENV": "/usr/share/Modules/init/bash", "GDM_LANG": "en_US.UTF-8", "HISTSIZE": "50000", "HOSTNAME": "font.ii.inmanta.com", "LC_CTYPE": "en_US.UTF-8", "LESSOPEN": "||/usr/bin/lesspipe.sh %s", "LSCOLORS": "Gxfxcxdxbxegedabagacad", "USERNAME": "wouter", "XDG_SEAT": "seat0", "XDG_VTNR": "2", "COLORTERM": "truecolor", "LS_COLORS": "rs=0:di=38;5;33:ln=38;5;51:mh=00:pi=40;38;5;11:so=38;5;13:do=38;5;5:bd=48;5;232;38;5;11:cd=48;5;232;38;5;3:or=48;5;232;38;5;9:mi=01;05;37;41:su=48;5;196;38;5;15:sg=48;5;11;38;5;16:ca=48;5;196;38;5;226:tw=48;5;10;38;5;16:ow=48;5;10;38;5;21:st=48;5;21;38;5;15:ex=38;5;40:*.tar=38;5;9:*.tgz=38;5;9:*.arc=38;5;9:*.arj=38;5;9:*.taz=38;5;9:*.lha=38;5;9:*.lz4=38;5;9:*.lzh=38;5;9:*.lzma=38;5;9:*.tlz=38;5;9:*.txz=38;5;9:*.tzo=38;5;9:*.t7z=38;5;9:*.zip=38;5;9:*.z=38;5;9:*.dz=38;5;9:*.gz=38;5;9:*.lrz=38;5;9:*.lz=38;5;9:*.lzo=38;5;9:*.xz=38;5;9:*.zst=38;5;9:*.tzst=38;5;9:*.bz2=38;5;9:*.bz=38;5;9:*.tbz=38;5;9:*.tbz2=38;5;9:*.tz=38;5;9:*.deb=38;5;9:*.rpm=38;5;9:*.jar=38;5;9:*.war=38;5;9:*.ear=38;5;9:*.sar=38;5;9:*.rar=38;5;9:*.alz=38;5;9:*.ace=38;5;9:*.zoo=38;5;9:*.cpio=38;5;9:*.7z=38;5;9:*.rz=38;5;9:*.cab=38;5;9:*.wim=38;5;9:*.swm=38;5;9:*.dwm=38;5;9:*.esd=38;5;9:*.jpg=38;5;13:*.jpeg=38;5;13:*.mjpg=38;5;13:*.mjpeg=38;5;13:*.gif=38;5;13:*.bmp=38;5;13:*.pbm=38;5;13:*.pgm=38;5;13:*.ppm=38;5;13:*.tga=38;5;13:*.xbm=38;5;13:*.xpm=38;5;13:*.tif=38;5;13:*.tiff=38;5;13:*.png=38;5;13:*.svg=38;5;13:*.svgz=38;5;13:*.mng=38;5;13:*.pcx=38;5;13:*.mov=38;5;13:*.mpg=38;5;13:*.mpeg=38;5;13:*.m2v=38;5;13:*.mkv=38;5;13:*.webm=38;5;13:*.ogm=38;5;13:*.mp4=38;5;13:*.m4v=38;5;13:*.mp4v=38;5;13:*.vob=38;5;13:*.qt=38;5;13:*.nuv=38;5;13:*.wmv=38;5;13:*.asf=38;5;13:*.rm=38;5;13:*.rmvb=38;5;13:*.flc=38;5;13:*.avi=38;5;13:*.fli=38;5;13:*.flv=38;5;13:*.gl=38;5;13:*.dl=38;5;13:*.xcf=38;5;13:*.xwd=38;5;13:*.yuv=38;5;13:*.cgm=38;5;13:*.emf=38;5;13:*.ogv=38;5;13:*.ogx=38;5;13:*.aac=38;5;45:*.au=38;5;45:*.flac=38;5;45:*.m4a=38;5;45:*.mid=38;5;45:*.midi=38;5;45:*.mka=38;5;45:*.mp3=38;5;45:*.mpc=38;5;45:*.ogg=38;5;45:*.ra=38;5;45:*.wav=38;5;45:*.oga=38;5;45:*.opus=38;5;45:*.spx=38;5;45:*.xspf=38;5;45:", "GDMSESSION": "gnome-xorg", "MODULEPATH": "/etc/scl/modulefiles:/etc/scl/modulefiles:/usr/share/Modules/modulefiles:/etc/modulefiles:/usr/share/modulefiles", "WINDOWPATH": "2", "XAUTHORITY": "/run/user/1000/gdm/Xauthority", "XMODIFIERS": "@im=ibus", "HISTCONTROL": "ignoredups", "MODULESHOME": "/usr/share/Modules", "MODULES_CMD": "/usr/share/Modules/libexec/modulecmd.tcl", "OS_AUTH_URL": "http://node2.ii.inmanta.com:5000/v3", "OS_PASSWORD": "21ce1521d8d344f3", "OS_USERNAME": "admin", "VIRTUAL_ENV": "/home/wouter/.virtualenvs/inmanta-pg", "VTE_VERSION": "5603", "WORKON_HOME": "/home/wouter/.virtualenvs", "QT_IM_MODULE": "ibus", "GUESTFISH_PS1": "\\\\[\\\\e[1;32m\\\\]><fs>\\\\[\\\\e[0;31m\\\\] ", "LOADEDMODULES": "", "SSH_AGENT_PID": "2255", "SSH_AUTH_SOCK": "/run/user/1000/keyring/ssh", "XDG_DATA_DIRS": "/home/wouter/.local/share/flatpak/exports/share/:/var/lib/flatpak/exports/share/:/usr/local/share/:/usr/share/", "GUESTFISH_INIT": "\\\\e[1;34m", "XDG_SESSION_ID": "2", "DESKTOP_SESSION": "gnome-xorg", "SESSION_MANAGER": "local/unix:@/tmp/.ICE-unix/2211,unix/unix:/tmp/.ICE-unix/2211", "XDG_MENU_PREFIX": "gnome-", "XDG_RUNTIME_DIR": "/run/user/1000", "GUESTFISH_OUTPUT": "\\\\e[0m", "XDG_SESSION_TYPE": "x11", "GUESTFISH_RESTORE": "\\\\e[0m", "XDG_SESSION_CLASS": "user", "MODULEPATH_modshare": "/usr/share/modulefiles:1:/usr/share/Modules/modulefiles:1:/etc/modulefiles:1", "PYTEST_CURRENT_TEST": "tests/db/dump_tool.py::test_dump_db (call)", "XDG_CURRENT_DESKTOP": "GNOME", "XDG_SESSION_DESKTOP": "gnome-xorg", "DESKTOP_AUTOSTART_ID": "10704fa85eea63dd5156957607823724100000022110007", "GNOME_TERMINAL_SCREEN": "/org/gnome/Terminal/screen/b641bf14_5790_4ce2_8b69_ea8a4164c5e9", "GNOME_TERMINAL_SERVICE": ":1.99", "MODULES_RUN_QUARANTINE": "LD_LIBRARY_PATH", "_VIRTUALENVWRAPPER_API": " mkvirtualenv rmvirtualenv lsvirtualenv showvirtualenv workon add2virtualenv cdsitepackages cdvirtualenv lssitepackages toggleglobalsitepackages cpvirtualenv setvirtualenvproject mkproject cdproject mktmpenv wipeenv allvirtualenv mkvirtualenv rmvirtualenv lsvirtualenv showvirtualenv workon add2virtualenv cdsitepackages cdvirtualenv lssitepackages toggleglobalsitepackages cpvirtualenv setvirtualenvproject mkproject cdproject mktmpenv wipeenv allvirtualenv", "OS_IDENTITY_API_VERSION": "3", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus", "VIRTUALENVWRAPPER_SCRIPT": "/usr/bin/virtualenvwrapper.sh", "VIRTUALENVWRAPPER_HOOK_DIR": "/home/wouter/.virtualenvs", "VIRTUAL_ENV_DISABLE_PROMPT": "1", "VIRTUALENVWRAPPER_WORKON_CD": "1", "VIRTUALENVWRAPPER_VIRTUALENV": "/usr/bin/venv", "VIRTUALENVWRAPPER_PROJECT_FILENAME": ".project"}	t	t	t	1569583847	305757bd-a368-4922-877c-4ab763810a34	t
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1569583841	d357482f-11c9-421e-b3c1-36d11ac5b975	2019-09-27 13:30:41.944528	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "wouter", "hostname": "font.ii.inmanta.com", "inmanta:compile:state": "success"}}	2	{}	{}
1569583847	d357482f-11c9-421e-b3c1-36d11ac5b975	2019-09-27 13:30:47.774146	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "wouter", "hostname": "font.ii.inmanta.com", "inmanta:compile:state": "success"}}	2	{}	{}
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings) FROM stdin;
173ed41e-5dcc-482a-9eb1-d1c7965f71b1	dev-2	7f178458-3184-4d4b-b67f-74bcf5d5dc8e			{}
d357482f-11c9-421e-b3c1-36d11ac5b975	dev-1	7f178458-3184-4d4b-b67f-74bcf5d5dc8e			{"auto_deploy": false, "server_compile": true, "autostart_on_start": true, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0}
\.


--
-- Data for Name: form; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.form (environment, form_type, options, fields, defaults, field_options) FROM stdin;
\.


--
-- Data for Name: formrecord; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.formrecord (id, form, environment, fields, changed) FROM stdin;
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata) FROM stdin;
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
7f178458-3184-4d4b-b67f-74bcf5d5dc8e	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
e786d359-062e-4f4b-af06-5661c621e17b	2019-09-27 13:30:37.84532	2019-09-27 13:30:37.848081		Init			0	08d17124-8cb4-4526-ad63-5af768fc98b7
1cd01b9f-b4b2-482e-8273-58e8e9665d44	2019-09-27 13:30:37.849394	2019-09-27 13:30:42.041036	/home/wouter/.virtualenvs/inmanta-pg/bin/python -m inmanta.app -vvv export -X -e d357482f-11c9-421e-b3c1-36d11ac5b975 --server_address localhost --server_port 58183 --metadata {"type": "api", "message": "Recompile trigger through API call"}	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           WARNING collecting reqs on project that has not been loaded completely\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002724)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 64, time: 0.002672)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 66, time: 0.000104)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:58183/api/v1/file\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:58183/api/v1/file/c4f8831d81b227edbef08fba76b4fa5477b58273\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:58183/api/v1/codebatched/1569583841\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:58183/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:58183/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1569583841\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1569583841\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:58183/api/v1/version\ninmanta.export           INFO    Committed resources with version 1569583841\n	0	08d17124-8cb4-4526-ad63-5af768fc98b7
e5b8fcad-a567-4dba-a66a-a57e55c2b755	2019-09-27 13:30:47.167961	2019-09-27 13:30:47.840809	/home/wouter/.virtualenvs/inmanta-pg/bin/python -m inmanta.app -vvv export -X -e d357482f-11c9-421e-b3c1-36d11ac5b975 --server_address localhost --server_port 58183 --metadata {"type": "api", "message": "Recompile trigger through API call"}	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    verifying project\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003175)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 64, time: 0.002684)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 66, time: 0.000094)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:58183/api/v1/file\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:58183/api/v1/codebatched/1569583847\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:58183/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1569583847\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1569583847\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:58183/api/v1/version\ninmanta.export           INFO    Committed resources with version 1569583847\n	0	616c9a73-9244-46b2-a77e-1523c2ce5274
9694a269-32dd-45af-af37-f7dafa7c5284	2019-09-27 13:30:47.164123	2019-09-27 13:30:47.166685		Init			0	616c9a73-9244-46b2-a77e-1523c2ce5274
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides) FROM stdin;
d357482f-11c9-421e-b3c1-36d11ac5b975	1569583841	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1569583841	localhost	2019-09-27 13:30:46.347644	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1569583841, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}
d357482f-11c9-421e-b3c1-36d11ac5b975	1569583841	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1569583841	internal	2019-09-27 13:30:47.019088	{"uri": "local:", "purged": false, "version": 1569583841, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}
d357482f-11c9-421e-b3c1-36d11ac5b975	1569583847	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1569583847	internal	2019-09-27 13:30:48.120003	{"uri": "local:", "purged": false, "version": 1569583847, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}
d357482f-11c9-421e-b3c1-36d11ac5b975	1569583847	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1569583847	localhost	2019-09-27 13:30:48.166654	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1569583847, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, send_event) FROM stdin;
28e4dfe8-e7c3-480c-8d73-6324e53c7452	store	2019-09-27 13:30:41.940437	2019-09-27 13:30:41.972235	{"{\\"msg\\": \\"Successfully stored version 1569583841\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1569583841}, \\"timestamp\\": \\"2019-09-27T13:30:41.972242\\"}"}	\N	{}	\N	\N
c5cb9606-0bf4-44e4-afaa-5ea34bf7be74	pull	2019-09-27 13:30:44.860026	2019-09-27 13:30:44.872448	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2019-09-27T13:30:44.872464\\"}"}	\N	{}	\N	\N
f4e52216-6ab2-43d3-89bc-f50726d7c43c	deploy	2019-09-27 13:30:45.613568	\N	\N	deploying	{}	\N	f
f2927914-89de-4286-a38e-751d1439edac	pull	2019-09-27 13:30:46.254591	2019-09-27 13:30:46.266549	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2019-09-27T13:30:46.266567\\"}"}	\N	{}	\N	\N
dccd78be-df68-4240-94e3-4d9b4ddd1ef5	deploy	2019-09-27 13:30:46.323843	2019-09-27 13:30:46.347644	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1569583841 because Repair run started at 2019-09-27 13:30:46\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2019-09-27 13:30:46\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1569583841\\", \\"deploy_id\\": \\"07cfd18f-b2c2-4f08-8dca-4bbff2399f71\\"}, \\"timestamp\\": \\"2019-09-27T13:30:46.323880\\"}","{\\"msg\\": \\"Start deploy 07cfd18f-b2c2-4f08-8dca-4bbff2399f71 of resource std::File[localhost,path=/tmp/test],v=1569583841\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"07cfd18f-b2c2-4f08-8dca-4bbff2399f71\\", \\"resource_id\\": {\\"version\\": 1569583841, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2019-09-27T13:30:46.323937\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1569583841 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 816, in execute\\\\n    self.update_resource(ctx, changes, desired)\\\\n  File \\\\\\"/tmp/tmp1xp_gsi7/d357482f-11c9-421e-b3c1-36d11ac5b975/agent/code/modules/inmanta_plugins.std.resources.py\\\\\\", line 187, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 589, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1569583841, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2019-09-27T13:30:46.347130\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1569583841 in deploy 07cfd18f-b2c2-4f08-8dca-4bbff2399f71\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1569583841\\", \\"deploy_id\\": \\"07cfd18f-b2c2-4f08-8dca-4bbff2399f71\\"}, \\"timestamp\\": \\"2019-09-27T13:30:46.347601\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1569583841": {"group": {"current": "wouter", "desired": "root"}, "owner": {"current": "wouter", "desired": "root"}}}	nochange	f
ace9fefd-186a-4e2a-b0f0-f03f944eb659	pull	2019-09-27 13:30:46.947582	2019-09-27 13:30:46.950003	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2019-09-27T13:30:46.950007\\"}"}	\N	{}	\N	\N
a54e566d-7549-4c19-b2a3-9e3ac1b94493	deploy	2019-09-27 13:30:47.000549	2019-09-27 13:30:47.019088	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1569583841 because Repair run started at 2019-09-27 13:30:46\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2019-09-27 13:30:46\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1569583841\\", \\"deploy_id\\": \\"40676fd5-762e-40c6-9cdc-7d433add0efb\\"}, \\"timestamp\\": \\"2019-09-27T13:30:47.000583\\"}","{\\"msg\\": \\"Start deploy 40676fd5-762e-40c6-9cdc-7d433add0efb of resource std::AgentConfig[internal,agentname=localhost],v=1569583841\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"40676fd5-762e-40c6-9cdc-7d433add0efb\\", \\"resource_id\\": {\\"version\\": 1569583841, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2019-09-27T13:30:47.000629\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1569583841 in deploy 40676fd5-762e-40c6-9cdc-7d433add0efb\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1569583841\\", \\"deploy_id\\": \\"40676fd5-762e-40c6-9cdc-7d433add0efb\\"}, \\"timestamp\\": \\"2019-09-27T13:30:47.019042\\"}"}	deployed	{}	nochange	f
bc267d38-6f04-4cec-82e6-557e0289b6ed	store	2019-09-27 13:30:47.77077	2019-09-27 13:30:47.78063	{"{\\"msg\\": \\"Successfully stored version 1569583847\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1569583847}, \\"timestamp\\": \\"2019-09-27T13:30:47.780642\\"}"}	\N	{}	\N	\N
93e4bd6f-3a99-4820-9d84-4de6907d208f	pull	2019-09-27 13:30:48.034754	2019-09-27 13:30:48.038553	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2019-09-27T13:30:48.038562\\"}"}	\N	{}	\N	\N
1499ac9c-f894-4a6f-8ae6-aa74b683140d	pull	2019-09-27 13:30:48.03552	2019-09-27 13:30:48.046321	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2019-09-27T13:30:48.046327\\"}"}	\N	{}	\N	\N
98b23c2e-17fa-48e7-b5a7-ba165ce3261e	deploy	2019-09-27 13:30:48.093413	2019-09-27 13:30:48.120003	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1569583847 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1569583847\\", \\"deploy_id\\": \\"2f8c9b7f-0d34-4386-9122-ffd1278f35eb\\"}, \\"timestamp\\": \\"2019-09-27T13:30:48.093527\\"}","{\\"msg\\": \\"Start deploy 2f8c9b7f-0d34-4386-9122-ffd1278f35eb of resource std::AgentConfig[internal,agentname=localhost],v=1569583847\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"2f8c9b7f-0d34-4386-9122-ffd1278f35eb\\", \\"resource_id\\": {\\"version\\": 1569583847, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2019-09-27T13:30:48.093586\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1569583847 in deploy 2f8c9b7f-0d34-4386-9122-ffd1278f35eb\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1569583847\\", \\"deploy_id\\": \\"2f8c9b7f-0d34-4386-9122-ffd1278f35eb\\"}, \\"timestamp\\": \\"2019-09-27T13:30:48.119958\\"}"}	deployed	{}	nochange	f
3c452019-974d-47f8-a81c-538572ec4510	deploy	2019-09-27 13:30:48.144379	2019-09-27 13:30:48.166654	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1569583847 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1569583847\\", \\"deploy_id\\": \\"836a3af3-fa1e-4e8c-9f5c-5f9dd7414d48\\"}, \\"timestamp\\": \\"2019-09-27T13:30:48.144412\\"}","{\\"msg\\": \\"Start deploy 836a3af3-fa1e-4e8c-9f5c-5f9dd7414d48 of resource std::File[localhost,path=/tmp/test],v=1569583847\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"836a3af3-fa1e-4e8c-9f5c-5f9dd7414d48\\", \\"resource_id\\": {\\"version\\": 1569583847, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2019-09-27T13:30:48.144459\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1569583847 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 816, in execute\\\\n    self.update_resource(ctx, changes, desired)\\\\n  File \\\\\\"/tmp/tmp1xp_gsi7/d357482f-11c9-421e-b3c1-36d11ac5b975/agent/code/modules/inmanta_plugins.std.resources.py\\\\\\", line 187, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 589, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1569583847, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2019-09-27T13:30:48.166191\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1569583847 in deploy 836a3af3-fa1e-4e8c-9f5c-5f9dd7414d48\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1569583847\\", \\"deploy_id\\": \\"836a3af3-fa1e-4e8c-9f5c-5f9dd7414d48\\"}, \\"timestamp\\": \\"2019-09-27T13:30:48.166615\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1569583847": {"group": {"current": "wouter", "desired": "root"}, "owner": {"current": "wouter", "desired": "root"}}}	nochange	f
\.


--
-- Data for Name: resourceversionid; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceversionid (environment, action_id, resource_version_id) FROM stdin;
d357482f-11c9-421e-b3c1-36d11ac5b975	28e4dfe8-e7c3-480c-8d73-6324e53c7452	std::File[localhost,path=/tmp/test],v=1569583841
d357482f-11c9-421e-b3c1-36d11ac5b975	28e4dfe8-e7c3-480c-8d73-6324e53c7452	std::AgentConfig[internal,agentname=localhost],v=1569583841
d357482f-11c9-421e-b3c1-36d11ac5b975	c5cb9606-0bf4-44e4-afaa-5ea34bf7be74	std::AgentConfig[internal,agentname=localhost],v=1569583841
d357482f-11c9-421e-b3c1-36d11ac5b975	f4e52216-6ab2-43d3-89bc-f50726d7c43c	std::AgentConfig[internal,agentname=localhost],v=1569583841
d357482f-11c9-421e-b3c1-36d11ac5b975	f2927914-89de-4286-a38e-751d1439edac	std::File[localhost,path=/tmp/test],v=1569583841
d357482f-11c9-421e-b3c1-36d11ac5b975	dccd78be-df68-4240-94e3-4d9b4ddd1ef5	std::File[localhost,path=/tmp/test],v=1569583841
d357482f-11c9-421e-b3c1-36d11ac5b975	ace9fefd-186a-4e2a-b0f0-f03f944eb659	std::AgentConfig[internal,agentname=localhost],v=1569583841
d357482f-11c9-421e-b3c1-36d11ac5b975	a54e566d-7549-4c19-b2a3-9e3ac1b94493	std::AgentConfig[internal,agentname=localhost],v=1569583841
d357482f-11c9-421e-b3c1-36d11ac5b975	bc267d38-6f04-4cec-82e6-557e0289b6ed	std::File[localhost,path=/tmp/test],v=1569583847
d357482f-11c9-421e-b3c1-36d11ac5b975	bc267d38-6f04-4cec-82e6-557e0289b6ed	std::AgentConfig[internal,agentname=localhost],v=1569583847
d357482f-11c9-421e-b3c1-36d11ac5b975	93e4bd6f-3a99-4820-9d84-4de6907d208f	std::AgentConfig[internal,agentname=localhost],v=1569583847
d357482f-11c9-421e-b3c1-36d11ac5b975	1499ac9c-f894-4a6f-8ae6-aa74b683140d	std::File[localhost,path=/tmp/test],v=1569583847
d357482f-11c9-421e-b3c1-36d11ac5b975	98b23c2e-17fa-48e7-b5a7-ba165ce3261e	std::AgentConfig[internal,agentname=localhost],v=1569583847
d357482f-11c9-421e-b3c1-36d11ac5b975	3c452019-974d-47f8-a81c-538572ec4510	std::File[localhost,path=/tmp/test],v=1569583847
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, current_version) FROM stdin;
core	2
\.


--
-- Data for Name: unknownparameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.unknownparameter (id, name, environment, source, resource_id, version, metadata, resolved) FROM stdin;
\.


--
-- Name: agent agent_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent
    ADD CONSTRAINT agent_pkey PRIMARY KEY (environment, name);


--
-- Name: agentinstance agentinstance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentinstance
    ADD CONSTRAINT agentinstance_pkey PRIMARY KEY (id);


--
-- Name: agentprocess agentprocess_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentprocess
    ADD CONSTRAINT agentprocess_pkey PRIMARY KEY (sid);


--
-- Name: code code_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.code
    ADD CONSTRAINT code_pkey PRIMARY KEY (environment, version, resource);


--
-- Name: compile compile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compile
    ADD CONSTRAINT compile_pkey PRIMARY KEY (id);


--
-- Name: configurationmodel configurationmodel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel
    ADD CONSTRAINT configurationmodel_pkey PRIMARY KEY (environment, version);


--
-- Name: dryrun dryrun_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dryrun
    ADD CONSTRAINT dryrun_pkey PRIMARY KEY (id);


--
-- Name: environment environment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environment
    ADD CONSTRAINT environment_pkey PRIMARY KEY (id);


--
-- Name: form form_form_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form
    ADD CONSTRAINT form_form_type_key UNIQUE (form_type);


--
-- Name: form form_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form
    ADD CONSTRAINT form_pkey PRIMARY KEY (environment, form_type);


--
-- Name: formrecord formrecord_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formrecord
    ADD CONSTRAINT formrecord_pkey PRIMARY KEY (id);


--
-- Name: parameter parameter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parameter
    ADD CONSTRAINT parameter_pkey PRIMARY KEY (id);


--
-- Name: project project_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_name_key UNIQUE (name);


--
-- Name: project project_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);


--
-- Name: report report_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report
    ADD CONSTRAINT report_pkey PRIMARY KEY (id);


--
-- Name: resource resource_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource
    ADD CONSTRAINT resource_pkey PRIMARY KEY (environment, resource_version_id);


--
-- Name: resourceaction resourceaction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction
    ADD CONSTRAINT resourceaction_pkey PRIMARY KEY (action_id);


--
-- Name: resourceversionid resourceversionid_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceversionid
    ADD CONSTRAINT resourceversionid_pkey PRIMARY KEY (environment, action_id, resource_version_id);


--
-- Name: schemamanager schemamanager_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schemamanager
    ADD CONSTRAINT schemamanager_pkey PRIMARY KEY (name);


--
-- Name: unknownparameter unknownparameter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_pkey PRIMARY KEY (id);


--
-- Name: agentinstance_expired_tid_endpoint_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agentinstance_expired_tid_endpoint_index ON public.agentinstance USING btree (tid, name, expired);


--
-- Name: agentinstance_process_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agentinstance_process_index ON public.agentinstance USING btree (process);


--
-- Name: agentprocess_env_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agentprocess_env_expired_index ON public.agentprocess USING btree (environment, expired);


--
-- Name: agentprocess_sid_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX agentprocess_sid_expired_index ON public.agentprocess USING btree (sid, expired);


--
-- Name: compile_env_remote_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_env_remote_id_index ON public.compile USING btree (environment, remote_id);


--
-- Name: compile_env_requested_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_env_requested_index ON public.compile USING btree (environment, requested);


--
-- Name: compile_env_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_env_started_index ON public.compile USING btree (environment, started DESC);


--
-- Name: configurationmodel_env_released_version_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX configurationmodel_env_released_version_index ON public.configurationmodel USING btree (environment, released, version DESC);


--
-- Name: configurationmodel_env_version_total_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX configurationmodel_env_version_total_index ON public.configurationmodel USING btree (environment, version DESC, total);


--
-- Name: dryrun_env_model_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dryrun_env_model_index ON public.dryrun USING btree (environment, model);


--
-- Name: environment_name_project_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX environment_name_project_index ON public.environment USING btree (project, name);


--
-- Name: formrecord_form_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX formrecord_form_index ON public.formrecord USING btree (form);


--
-- Name: parameter_env_name_resource_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parameter_env_name_resource_id_index ON public.parameter USING btree (environment, name, resource_id);


--
-- Name: parameter_metadata_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parameter_metadata_index ON public.parameter USING gin (metadata jsonb_path_ops);


--
-- Name: parameter_updated_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parameter_updated_index ON public.parameter USING btree (updated);


--
-- Name: report_compile_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_compile_index ON public.report USING btree (compile);


--
-- Name: resource_attributes_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_attributes_index ON public.resource USING gin (attributes jsonb_path_ops);


--
-- Name: resource_env_attr_hash_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_env_attr_hash_index ON public.resource USING btree (environment, attribute_hash);


--
-- Name: resource_env_model_agent_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_env_model_agent_index ON public.resource USING btree (environment, model, agent);


--
-- Name: resource_env_resourceid_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_env_resourceid_index ON public.resource USING btree (environment, resource_id, model DESC);


--
-- Name: resourceaction_action_id_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX resourceaction_action_id_started_index ON public.resourceaction USING btree (action_id, started DESC);


--
-- Name: resourceaction_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_started_index ON public.resourceaction USING btree (started);


--
-- Name: resourceversionid_action_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceversionid_action_id_index ON public.resourceversionid USING btree (action_id);


--
-- Name: resourceversionid_environment_resource_version_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceversionid_environment_resource_version_id_index ON public.resourceversionid USING btree (environment, resource_version_id);


--
-- Name: unknownparameter_env_version_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX unknownparameter_env_version_index ON public.unknownparameter USING btree (environment, version);


--
-- Name: unknownparameter_resolved_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX unknownparameter_resolved_index ON public.unknownparameter USING btree (resolved);


--
-- Name: agent agent_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent
    ADD CONSTRAINT agent_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: agent agent_id_primary_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent
    ADD CONSTRAINT agent_id_primary_fkey FOREIGN KEY (id_primary) REFERENCES public.agentinstance(id) ON DELETE CASCADE;


--
-- Name: agentinstance agentinstance_process_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentinstance
    ADD CONSTRAINT agentinstance_process_fkey FOREIGN KEY (process) REFERENCES public.agentprocess(sid) ON DELETE CASCADE;


--
-- Name: agentprocess agentprocess_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentprocess
    ADD CONSTRAINT agentprocess_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: code code_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.code
    ADD CONSTRAINT code_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: compile compile_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compile
    ADD CONSTRAINT compile_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: configurationmodel configurationmodel_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel
    ADD CONSTRAINT configurationmodel_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: dryrun dryrun_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dryrun
    ADD CONSTRAINT dryrun_environment_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: environment environment_project_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environment
    ADD CONSTRAINT environment_project_fkey FOREIGN KEY (project) REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: form form_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form
    ADD CONSTRAINT form_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: formrecord formrecord_form_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formrecord
    ADD CONSTRAINT formrecord_form_fkey FOREIGN KEY (form) REFERENCES public.form(form_type) ON DELETE CASCADE;


--
-- Name: parameter parameter_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parameter
    ADD CONSTRAINT parameter_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: report report_compile_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report
    ADD CONSTRAINT report_compile_fkey FOREIGN KEY (compile) REFERENCES public.compile(id) ON DELETE CASCADE;


--
-- Name: resource resource_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource
    ADD CONSTRAINT resource_environment_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: resourceversionid resourceversionid_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceversionid
    ADD CONSTRAINT resourceversionid_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.resourceaction(action_id) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_fkey1 FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

