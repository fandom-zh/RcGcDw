cd ..
declare -a StringArray=("rcgcdw" "misc")
for file in ${StringArray[@]}; do
  xgettext -L Python --package-name=RcGcDw -L Python --keyword=pgettext:1c,2 --keyword=npgettext:1c,2,3 -o "locale/templates/$file.pot" src/$file.py
done
# Get all translatable files for formatters
find extensions/ -name '*.py' -print | xargs xgettext -L Python --package-name=RcGcDw --keyword=pgettext:1c,2 --keyword=npgettext:1c,2,3 -o "locale/templates/formatters.pot" src/api/util.py
for language in de fr lol pl pt-br ru uk zh-hans zh-hant hi es
do
  for file in ${StringArray[@]}; do
    msgmerge -U locale/$language/LC_MESSAGES/$file.po locale/templates/$file.pot
  done
done
# Exceptions
xgettext -L Python --package-name=RcGcDw --keyword=pgettext:1c,2 --keyword=npgettext:1c,2,3 -o "locale/templates/redaction.pot" src/discord/redaction.py
for language in de fr lol pl pt-br ru uk zh-hans zh-hant hi es
do
  msgmerge -U locale/$language/LC_MESSAGES/redaction.po locale/templates/redaction.pot
  msgmerge -U locale/$language/LC_MESSAGES/formatters.po locale/templates/formatters.pot
done
