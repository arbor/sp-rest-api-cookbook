FROM ubuntu
RUN apt-get update
RUN apt-get install -y tzdata
RUN apt-get install -y emacs
RUN apt-get install -y texlive
RUN apt-get install -y texlive-pictures
RUN apt-get install -y texlive-latex-extra
RUN apt-get install -y python-pygments
COPY export.el /
COPY render.sh /
ENTRYPOINT ["/bin/bash", "render.sh"]
