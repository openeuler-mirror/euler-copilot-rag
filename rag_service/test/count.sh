log_file=/rag-service/logs/app.log
result_file=/rag-service/rag_service/test/result.txt
# echo "" > $result_file

echo "User " $1 >> $result_file
echo "" >> $result_file

# Timeout count
time_out_count=$(grep -oP 'Read timed out\.\]' $log_file | awk '{count++} END {print count}')
echo "Read time out:" $time_out_count >> $result_file

# Query rewrite
read -r avg <<< "$(grep -oP 'query rewrite: \K[0-9.]+' $log_file | awk '{sum+=$1; total++} END {print sum/total}')"
echo "Query rewrite avg:" $avg >> $result_file

# Query generate
#read -r avg <<< "$(grep -oP 'query generate: \K[0-9.]+' $log_file | awk '{sum+=$1; total++} END {print sum/total}')"
#echo "Query generate:" $avg >> $result_file

# Neo4j entity extract
read -r avg <<< "$(grep -oP 'neo4j entity extract: \K[0-9.]+' $log_file | awk '{sum+=$1; total++} END {print sum/total}')"
echo "Neo4j entity extract avg:" $avg >> $result_file

# Neo4j search
read -r avg <<< "$(grep -oP 'neo4j search: \K[0-9.]+' $log_file | awk '{sum+=$1; total++} END {print sum/total}')"
echo "Neo4j search avg:" $avg >> $result_file

# Pgvector search
read -r avg <<< "$(grep -oP 'pgvector search: \K[0-9.]+' $log_file | awk '{sum+=$1; total++} END {print sum/total}')"
echo "Pgvector search avg:" $avg >> $result_file

# First content avg
read -r avg total <<< "$(grep -oP 'first content: \K[0-9.]+' $log_file | awk '{sum+=$1; total++} END {print sum/total, total}')"
echo "First content avg:" $avg >> $result_file
echo "Total:" $total >> $result_file

# Finish content avg
read -r avg total <<< "$(grep -oP 'finish time: \K[0-9.]+' $log_file | awk '{sum+=$1; total++} END {print sum/total, total}')"
echo "Finish content avg:" $avg >> $result_file
echo "Total:" $total >> $result_file

echo "" >> $result_file
echo "" >> $result_file