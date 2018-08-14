FROM ubuntu
RUN apt-get update
RUN apt-get install -y tzdata
RUN apt-get install -y emacs
RUN apt-get install -y texlive
RUN apt-get install -y texlive-pictures
RUN apt-get install -y texlive-latex-extra
RUN apt-get install -y python-pygments
RUN apt-get install -y ditaa
RUN mkdir -p /usr/share/emacs/25.2/lisp/contrib/scripts/
RUN /bin/ln -s /usr/share/ditaa/ditaa.jar /usr/share/emacs/25.2/lisp/contrib/scripts/
COPY export.el /
COPY render.sh /
ENTRYPOINT ["/bin/bash", "render.sh"]
