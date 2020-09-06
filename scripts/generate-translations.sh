cd ..
declare -a StringArray=("discussion_formatters" "rc_formatters" "rcgcdw" "rc" "misc")
for file in ${StringArray[@]}; do
  xgettext -L Python --package-name=RcGcDw -o "locale/templates/$file.pot" src/$file.py
done
for language in de fr lol pl pt-br ru uk zh_Hans zh_Hant
do
  for file in ${StringArray[@]}; do
    msgmerge -U locale/$language/LC_MESSAGES/$file.po locale/templates/$file.pot
  done
done
