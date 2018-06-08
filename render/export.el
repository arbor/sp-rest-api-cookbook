(setq kill-buffer-query-functions
  (remove 'process-kill-buffer-query-function
   kill-buffer-query-functions))

(require 'org)
(require 'ox-latex)
(add-to-list 'org-latex-classes
	     '("tufte-book"
	       "\\documentclass{tufte-book}"
               ("\\chapter{%s}" . "\\chapter*{%s}")
               ("\\section{%s}" . "\\section*{%s}")
               ("\\subsection{%s}" . "\\subsection*{%s}")
               ("\\subsubsection{%s}" . "\\subsubsection*{%s}")))
;;;;
;;
;; https://github.com/syl20bnr/spacemacs/issues/7055
;;
;; Use minted
(add-to-list 'org-latex-packages-alist '("" "minted"))
(setq org-latex-listings 'minted)
(setq org-latex-minted-options '(
                                 ("frame" "lines")
                                 ("fontsize" "\\scriptsize")
                                 ("xleftmargin" "\\parindent")
                                 ("linenos" "")
                                 ("breaklines" "")
                                 ("breakafter" "+")
                                 ))

(setq org-export-with-smart-quotes t)
