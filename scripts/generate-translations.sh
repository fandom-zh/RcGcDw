cd ..
declare -a StringArray=("discussion_formatters" "rc_formatters" "rcgcdw" "rc" "misc")
for file in ${StringArray[@]}; do
  xgettext -L Python --package-name=RcGcDw -o "locale/templates/$file.pot" src/$file.py
done
for language in de fr lol pl pt-br ru uk zh_Hans zh_Hant hi
do
  for file in ${StringArray[@]}; do
    msgmerge -U locale/$language/LC_MESSAGES/$file.po locale/templates/$file.pot
  done
done
# Exceptions
xgettext -L Python --package-name=RcGcDw -o "locale/templates/redaction.pot" src/discord/redaction.py
for language in de fr lol pl pt-br ru uk zh_Hans zh_Hant hi
do
  msgmerge -U locale/$language/LC_MESSAGES/redaction.po locale/templates/redaction.pot
done