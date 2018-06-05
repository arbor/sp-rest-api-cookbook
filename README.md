# Using the Arbor Networks SP REST API: SP v8.3 API v3

This repository contains the source material for a document that is
intended to be a gentle, user-facing introduction to the Arbor
Networks SP REST API.

## Formatting

The file `sp-rest-api-tutorial.txt` is formatted according to
[Emacs Orgmode](http://orgmode.org/guide/) formatting rules.  You
don't need Emacs or Orgmode to edit this file; the examples in the
file should be sufficient guidance for adding to it and the link to
the [Orgmode Guide](http://orgmode.org/guide/) may also help.

## Contributing

All contributions are greatly appreciated; pull requests, emailed
patches, emailed edits, printed and written-on paper, whatever works
easiest for you.  If you are interested in using Git to contribute,
see the section below titled **Working with Github forks, branches,
and pull requests**

## Rendering

If you want to render this you can use Emacs+Orgmode's Export (`C-e`)
command to produce HTML, PDF, etc.

Exporting from Emacs Orgmode as a LaTeX file is the easiest thing to
do, then, assuming you have the LaTeX packages that are required, you
can run the commands:

   pdflatex -shell-escape sp-rest-api-tutorial
   pdflatex -shell-escape sp-rest-api-tutorial
   makeindex sp-rest-api-tutorial
   pdflatex -shell-escape sp-rest-api-tutorial

to produce a PDF file.

## Releases

Rendered versions will be released periodically at this Github site;
unless you are intending to contribute or want to render your own
version, the rendered releases are probably the best option for you.  The
releases are at
<a href=https://github.com/arbor/sp-rest-api-cookbook/releases>https://github.com/arbor/sp-rest-api-cookbook/releases</a>

In addition, there is a rendered HTML version available at
<a href=https://arbor.github.io/sp-rest-api-cookbook/sp-rest-api-tutorial.html>https://arbor.github.io/sp-rest-api-cookbook/sp-rest-api-tutorial.html</a>.

## Working with Github forks, branches, and pull requests

1.  Create an account on GitHub that you want to use for this work, or
    use an existing one.
2.  Log in to <http://github.com> as that account, go to
    <https://github.com/arbor/sp-rest-api-cookbook>, and click the
    Fork button in the upper right corner of the page. Alernatively
    use the [hub](https://hub.github.com/) git wrapper and Github
    client and type:

    ```sh
    hub clone git@github.com:arbor/sp-rest-api-cookbook.git
    cd sp-rest-api-cookbook
    hub fork
    ```
3.  Copy your fork to your computer by cloning it:

    ```sh
    git clone git@github.com:<YOUR_GITHUB_ACCOUNT_NAME>/sp-rest-api-cookbook.git
    cd sp-rest-api-cookbook
    ```
4.  Add a remote called 'upstream' to keep up with the version of this
    at Arbor's github site:

    ```sh
    git remote add upstream git@github.com:arbor/sp-rest-api-cookbook.git
    ```
5.  Create a git branch and switch to it:

    ```sh
    git checkout -b <branchname>
    ```
6.  Make your edits to `sp-rest-api-cookbook.txt`, add files to
    `code-examples` and `images`, etc.
7.  To track your work you can make as many commits as you want, they
    will all be merged together in a later step
8.  When you are done and ready to start the process of making a pull
    request, first update your `master` branch relative to the Arbor
    master branch (`upstream`) by typing:

    ```sh
    git checkout master
    git pull upstream master
    ```
9.  Then merge any changes into your branch; this will make the pull
    request match the most recent version at Arbor, thus making it
    easier and more likely the be accepted

    ```sh
    git checkout <branchname>
    git merge master
    ```

    You may need to make changes to your branch to get the merge to
    complete cleanly
10. Next type:

    ```sh
    git rebase -i master
    ```

    and change all of the lines after the first one to start with `s`
    instead of with `pick`; this will squash all of the changes into
    one commit; you'll have a chance to edit together all of the
    commit messages in the next step
11. Edit together all of your commit messages, check out some other
    commit messages to see the style (These can be seen by running
    `git log` in the repository)
12. Push your branch to Github into your own, forked, repository:

    ```sh
    git push -u origin <branchname>
    ```
13. On the github.com website, choose your branch of the repo and
    click "Issue Pull Request", edit the message and click submit. Or,
    if you're using `hub`:

    ```sh
    hub pull-request -b arbor/sp-rest-api-cookbook:master -h <your_git_id>:<your_branch_name>
    ```

    and fill out the message and title in the editor that starts up
14. You will get some emails from github when your PR is merged or
    rejected or commented on.
15. Once your PR is accepted and merged, you can update your master
    branch from the new upstream and delete your local feature branch:

    ```sh
    git pull upstream master
    git branch -d <branchname>
    ```

    then you can push the new master back to your github repository
    and delete the remote copy of your branch, making the master
    branch of your fork the same as the master branch of the copy in
    Arbor's github site:

    ```sh
    git push origin --delete <branchname>
    ```
16. Now you can return to step 5 and make more contributions!
