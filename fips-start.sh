sudo kill -9 $(sudo lsof -t -i :5354)
sudo ./fips/target/release/fips -c config.yaml