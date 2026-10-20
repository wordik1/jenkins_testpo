pipeline{
    agent any
    environment{
        IMAGE = "./obmc-phosphor-image-romulus-20250902012112.static.mtd"
        PATH = "/opt/venv/bin:${PATH}"
    }
    stages{
        stage('QEMU Start'){
            steps{
                sh '''
                    mkdir -p reports
                    nohup qemu-system-arm -m 256 -M romulus-bmc -nographic -snapshot \
                        -drive file=$IMAGE,format=raw,if=mtd \
                        -net nic \
                        -net user,hostfwd=tcp::2222-:22,hostfwd=tcp::2443-:443,hostfwd=udp::2623-:623,hostname=qemu \
                        > reports/qemu.log 2>&1 < /dev/null &
                    echo $! > qemu.pid

                    for i in $(seq 1 60); do
                        code=$(curl -ks -o /dev/null -w '%{http_code}' https://localhost:2443/redfish/v1/ || true)
                        [ "$code" = "200" ] && break
                        sleep 10
                    done
                    [ "$code" = "200" ] || { echo "BMC не загрузился"; exit 1; }
                    sleep 30

                    # пользователь для теста блокировки аккаунта (Selenium)
                    curl -ks --retry 5 --retry-all-errors --retry-delay 10 -u root:0penBmc \
                        -X POST -H 'Content-Type: application/json' \
                        -d '{"UserName":"locktest","Password":"TestPass123","RoleId":"Administrator"}' \
                        https://localhost:2443/redfish/v1/AccountService/Accounts \
                        | tee reports/qemu_setup.txt
                '''
            }
        }

        stage('Test OpenBMC'){
            steps{
                sh 'pgrep -a qemu || echo "qemu не запущен"; tail -n 20 reports/qemu.log || true; curl -ks -o /dev/null -w "%{http_code}\\n" https://127.0.0.1:2443/redfish/v1/ || true'
                sh 'xvfb-run -a pytest openbmc_auth_tests.py --html=reports/webui.html --self-contained-html'
            }
        }

        stage('Test Redfish'){
            steps{
                sh 'pytest test_redfish.py --html=reports/redfish.html --self-contained-html'
            }
        }

        stage('Test locust'){
            steps{
                sh '''
                    locust -f locustfile.py --headless -u 5 -r 1 -t 30s \
                        --host https://127.0.0.1:2443 \
                        --csv reports/locust --html reports/locust.html
                '''
            }
        }
    }
    post{
        always{
            echo 'Остановка qemu'
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
            sh 'pkill qemu-system-arm || true'
        }
    }
}