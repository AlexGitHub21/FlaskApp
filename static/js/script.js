$(function(){
        var currentTestId;
	        $('button#get_answer').click(function(){
		        var test_id = $(this).data('test_id');

		        $.ajax({
                    url: '/get_answer',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ test_id: test_id }),
                    success: function(response){
                        console.log('Ответ от сервера: ', response);

                        if (response.answer) {
                            // Если ответ успешно получен
                            var answerHtml = '<span class="badge badge-success">' + response.answer + '</span>';

                            // Найдем строку с данным test_id
                            var row = $('button[data-test_id="' + test_id + '"]').closest('tr');

                            // Удаляем кнопку и заменяем ее ответом
                            row.find('td').eq(4).html(answerHtml);
                        } else {
                            console.log(response.error);
                        }
                    },
                    error: function(error){
                        console.log('Ошибка: ', error);
                    }
		        });
	        });

	        $('button#delete_test').click(function(){
		        var test_id = $(this).data('test_id');

		        $.ajax({
                    url: '/delete_test',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ test_id: test_id }),
                    success: function(response){
                        console.log('Ответ от сервера: ', response);
                        $('button[data-test_id="' + test_id + '"]').closest('tr').remove();
                    },
                    error: function(error){
                        console.log('Ошибка: ', error);
                    }
		        });
	        });

            $('button#change_test').click(function() {
                var test_id = $(this).data('test_id');
                window.location.href = '/change_test/' + test_id;
            });
        });