#!/usr/bin/bash

res=0
module_count=0
GLOBAL_PYLINT_SCORE=0

if [ -n "$CI_PROJECT_DIR" ]
  then
    LINT_PATH=$CI_PROJECT_DIR/
    pylintc=${LINT_PATH}pylintrc.prod
elif [ -n "$1" ]
  then
    LINT_PATH="$1/"
    pylintc=${LINT_PATH}pylintrc.prod
  else
    LINT_PATH="$(pwd)/"
    pylintc=${LINT_PATH}.pylintrc
fi
cd $LINT_PATH

echo "Lint Path: $LINT_PATH --- pylintrc path: $pylintc"

export PYLINTRC=$pylintc

source $(pwd)/odoo.env

change_list=$(git diff --name-only HEAD HEAD~1 | xargs dirname | grep -v '\.' | cut -d '/' -f 1 | sort | uniq)

if [[ -z $change_list ]]
then
  echo "No module changes, skip linting"
  exit 0
fi

for d in $change_list
do
    cd $LINT_PATH
    if ! [ -d "$d" ]
    then
        echo "Skipping $d"
        continue
    fi
    if [[ $d == '.' ]]
    then
        continue
    fi
    if grep -Fx "$d" .pylintignore
    then
        echo "Skipping $d, ignored in .pylintignore"
        continue
    fi
    echo "${LINT_PATH}$d"
    cd "${LINT_PATH}$d"
    printf "\n\n\n"
    pwd
    module_count=$(($module_count+1))
    pylint --init-hook="$LINT_HOOK" --output-format=pylint_gitlab.GitlabCodeClimateReporter $(pwd) > ${LINT_PATH}$d/ql.json
    pylint --init-hook="$LINT_HOOK" --output-format=text $(pwd) >  ${LINT_PATH}$d/pylint.log || pylint-exit $?
    sed -n 's/^Your code has been rated at \([-0-9.]*\)\/.*/\1/p' ${LINT_PATH}$d/pylint.log > ${LINT_PATH}$d/.pylint_score
    PYLINT_SCORE=$(cat ${LINT_PATH}$d/.pylint_score)
    GLOBAL_PYLINT_SCORE=$(python3 -c "print( $GLOBAL_PYLINT_SCORE + max($PYLINT_SCORE, 0) )")
    cat ${LINT_PATH}$d/pylint.log
    echo "^^ $d - PYLINT SCORE: $PYLINT_SCORE - PYLINT GLOBAL SCORE: $GLOBAL_PYLINT_SCORE ^^"
    echo "==================="
done

echo "GLOBAL_PYLINT_SCORE: $GLOBAL_PYLINT_SCORE - module_count: $module_count"

if [ $module_count -ge 1 ]
  then
    GLOBAL_PYLINT_SCORE=$(python3 -c "print( $GLOBAL_PYLINT_SCORE/ float($module_count) )")
  else
    GLOBAL_PYLINT_SCORE=10
fi

echo "PYLINT SCORE: $GLOBAL_PYLINT_SCORE"

test "$res" == "0"
