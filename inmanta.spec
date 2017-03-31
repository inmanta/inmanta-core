# Use release 0 for prerelease version.
%define release 1
%define version 2017.2
%define venv %{buildroot}/opt/inmanta
%define _p3 %{venv}/bin/python3

%define sourceversion %{version}%{?buildid}

Name:           python3-inmanta
Version:        %{version}

Release:        %{release}%{?buildid}%{?tag}%{?dist}
Summary:        Inmanta automation and orchestration tool

Group:          Development/Languages
License:        LGPLv2+
URL:            http://inmanta.com
Source0:        inmanta-%{sourceversion}.tar.gz
Source1:        deps-%{version}.tar.gz
Source2:        inmanta-dashboard-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  systemd
BuildRequires:  sed

Requires:       git
Requires(pre):  shadow-utils

%if 0%{?rhel}
BuildRequires:  python34-devel
BuildRequires:  python34-pip
BuildRequires:  curl
Requires:       python34
%define __python3 /usr/bin/python3
%else
BuildRequires:  python3-devel
BuildRequires:  python3-pip
Requires:       python3
%endif

%package server
Summary:        The configuration and service files to start the Inmanta server

%package agent
Summary:        The configuration and service files to start the Inmanta agent

%description

%description server

%description agent

%prep
%setup -q -n inmanta-%{sourceversion}
%setup -T -D -a 1 -n inmanta-%{sourceversion}
%setup -T -D -a 2 -n inmanta-%{sourceversion}

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/inmanta
%if 0%{?rhel}
# venv is broken in epel, install pip manually
%{__python3} -m venv --without-pip %{venv}
curl https://bootstrap.pypa.io/get-pip.py | %{_p3}
rm %{buildroot}/opt/inmanta/pip-selfcheck.json
%else
%{__python3} -m venv %{venv}
%endif
%{_p3} -m pip install -U --no-index --find-links deps-%{version} wheel setuptools virtualenv pip
%{_p3} -m pip install --no-index --find-links deps-%{version} inmanta
%{_p3} -m inmanta.app

# Use the correct python for bycompiling
%define __python %{_p3}

# Fix shebang
sed -i "s|%{buildroot}||g" %{venv}/bin/*
find %{venv} -name RECORD | xargs sed -i "s|%{buildroot}||g"

# Put symlinks
mkdir -p %{buildroot}%{_bindir}
ln -s /opt/inmanta/bin/inmanta %{buildroot}%{_bindir}/inmanta
ln -s /opt/inmanta/bin/inmanta-cli %{buildroot}%{_bindir}/inmanta-cli

# Additional dirs and config
chmod -x LICENSE
mkdir -p %{buildroot}%{_localstatedir}/lib/inmanta
mkdir -p %{buildroot}/etc/inmanta
mkdir -p %{buildroot}/var/log/inmanta
install -p -m 644 misc/inmanta.cfg %{buildroot}/etc/inmanta.cfg

# Setup systemd
mkdir -p %{buildroot}%{_unitdir}
install -p -m 644 misc/inmanta-agent.service $RPM_BUILD_ROOT%{_unitdir}/inmanta-agent.service
install -p -m 644 misc/inmanta-server.service $RPM_BUILD_ROOT%{_unitdir}/inmanta-server.service

# Install the dashboard
cp -a dist %{venv}/dashboard
cat > %{buildroot}/etc/inmanta/server.cfg <<EOF
[dashboard]
enabled=true
path=/opt/inmanta/dashboard
EOF

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE docs/*
/opt/inmanta/bin
/opt/inmanta/lib
/opt/inmanta/lib64
/opt/inmanta/include
/opt/inmanta/pyvenv.cfg
%{_bindir}/inmanta
%{_bindir}/inmanta-cli
%attr(-, inmanta, inmanta) %{_localstatedir}/lib/inmanta
%config %attr(-, root, root) /etc/inmanta.cfg
%attr(-, inmanta, inmanta) /var/log/inmanta
%attr(-, root, root)/etc/inmanta

%files server
/opt/inmanta/dashboard
%attr(-,root,root) %{_unitdir}/inmanta-server.service

%files agent
%attr(-,root,root) %{_unitdir}/inmanta-agent.service

%post agent
%systemd_post inmanta-agent.service

%preun agent
%systemd_preun inmanta-server.service

%postun agent
%systemd_postun_with_restart inmanta-server.service

%post server
%systemd_post inmanta-agent.service

%preun server
%systemd_preun inmanta-server.service

%postun server
%systemd_postun_with_restart inmanta-server.service

%pre
getent group inmanta >/dev/null || groupadd -r inmanta
getent passwd inmanta >/dev/null || \
    useradd -r -g inmanta -d /var/lib/inmanta -s /bin/bash \
    -c "Account used by the Inmanta daemons" inmanta
exit

%changelog
* Mon May 30 2016 Bart Vanbrabant <bart.vanbrabant@inmanta.com> - 2016.3
- Rename to Inmanta

* Thu Jan 08 2015 Bart Vanbrabant <bart.vanbrabant@inmanta.com> - 0.1
- Initial release

