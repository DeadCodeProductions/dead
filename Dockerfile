FROM archlinux:latest

RUN pacman -Syyu --noconfirm --noprogressbar &&\
    pacman -S --noconfirm --needed --noprogressbar base-devel

# Adding user
RUN /usr/sbin/groupadd --system sudo && \
    /usr/sbin/useradd --create-home \
                      --groups sudo \
                      --uid 1337 --user-group \
                      dead && \
    /usr/sbin/sed -i -e "s/Defaults    requiretty.*/ #Defaults    requiretty/g" /etc/sudoers && \
    /usr/sbin/echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER dead
WORKDIR /home/dead

# Installing yay 11.1.1
RUN sudo pacman -S --noconfirm --noprogressbar git
RUN git clone https://aur.archlinux.org/yay.git &&\ 
    cd yay &&\ 
    git checkout cdf06b6781263e24d98754a99d70857aa959f691 &&\
    makepkg -si --noconfirm --noprogressbar
RUN rm -r yay/

# Installing dependencies
# These need compilation
RUN yay -S --noconfirm --noprogressbar csmith\
                                        creduce-git\
                                        compcert-git

# These don't
RUN yay -S --noconfirm --noprogressbar python\
                                        python-pip\
                                        gcc\
                                        clang\
                                        llvm\
                                        compiler-rt\
                                        cmake\
                                        boost\
                                        ninja\
                                        entr

COPY --chown=dead callchain_checker/ ./callchain_checker/

RUN mkdir /home/dead/callchain_checker/build/ &&\
    cd /home/dead/callchain_checker/build/ &&\
    cmake .. &&\
    make -j

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

RUN mkdir /home/dead/.config/dead/

RUN python3 -c 'from pathlib import Path; from dead_instrumenter import utils; utils.make_config(Path.home() / ".config/dead/instrumenter.json", True)'

COPY dockerconfig.json /home/dead/.config/dead/config.json

COPY --chown=dead patches/ /home/dead/patches/

COPY --chown=dead ./run_parallel.sh /home/dead/run_parallel.sh
