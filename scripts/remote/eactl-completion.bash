# eactl-completion.bash — makes the Tab key finish eactl commands for you.
#
#   eactl st<Tab>                 -> eactl status
#   eactl status de<Tab>          -> eactl status demo-u-u3fyig
#   eactl logs demo-u-u3fyig dj<Tab>  -> ... django
#
# Schools complete by their short name: it has no spaces, so it completes
# cleanly. (Commands also accept the display name, typed in quotes.)
#
# `eactl init` copies this into /etc/bash_completion.d/, which bash reads when a
# new terminal opens. So after init, open a new terminal (or log in again).

_eactl() {
    local cur prev cmd
    cur="${COMP_WORDS[COMP_CWORD]}"
    cmd="${COMP_WORDS[1]:-}"

    # The first word after eactl: the command.
    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "help init check apply-cluster apply-db new list update status logs shell setup-code make-admin remove" -- "$cur") )
        return
    fi

    # The second word, for commands that take a school: the schools' short names,
    # read from the cluster each time, so a new school completes straight away.
    if [ "$COMP_CWORD" -eq 2 ]; then
        case "$cmd" in
            update|status|logs|shell|setup-code|make-admin|remove)
                local schools
                schools="$(KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}" kubectl get namespaces -l ea/school \
                    -o jsonpath='{range .items[*]}{.metadata.labels.ea/school}{" "}{end}' 2>/dev/null)"
                [ "$cmd" = update ] && schools="$schools --all"
                COMPREPLY=( $(compgen -W "$schools" -- "$cur") )
                ;;
        esac
        return
    fi

    # The third word for logs: which part.
    if [ "$COMP_CWORD" -eq 3 ] && [ "$cmd" = logs ]; then
        COMPREPLY=( $(compgen -W "django react mosquitto mqtt-listener monitoring-publisher setup" -- "$cur") )
        return
    fi

    # Options.
    case "$cmd" in
        update) COMPREPLY=( $(compgen -W "--all --version" -- "$cur") ) ;;
        new)    COMPREPLY=( $(compgen -W "--version --address" -- "$cur") ) ;;
    esac
}

complete -F _eactl eactl
