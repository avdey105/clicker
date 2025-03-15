<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST');
header('Access-Control-Allow-Headers: Content-Type');

class DatabaseHandler {
    private $db;

    public function __construct() {
        try {
            $this->db = new SQLite3('../../telegrambot/users.db'); // Исправленный путь
            
            // Создаем таблицу для таймера, если её нет
            $this->db->exec('
                CREATE TABLE IF NOT EXISTS timer (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    end_time INTEGER NOT NULL
                )
            ');
            
            // Проверяем, есть ли запись таймера
            $result = $this->db->query('SELECT end_time FROM timer WHERE id = 1');
            if (!$result->fetchArray()) {
                // Если записи нет, создаем её (8 дней от текущего времени)
                $endTime = time() + (8 * 24 * 60 * 60);
                $this->db->exec("INSERT INTO timer (id, end_time) VALUES (1, $endTime)");
            }
        } catch (Exception $e) {
            $this->sendError('Database connection error: ' . $e->getMessage());
        }
    }

    private function sendResponse($data) {
        echo json_encode($data);
        exit;
    }

    private function sendError($message) {
        $this->sendResponse(['error' => $message]);
    }

public function checkUser($userId, $username = null) {
    try {
        $stmt = $this->db->prepare('SELECT * FROM users WHERE user_id = :user_id');
        $stmt->bindValue(':user_id', $userId, SQLITE3_INTEGER);
        $result = $stmt->execute();
        $user = $result->fetchArray(SQLITE3_ASSOC);
        
        if ($user) {
            $this->sendResponse([
                'exists' => true,
                'user' => $user
            ]);
        } else {
            // Автоматически добавляем пользователя
            $stmt = $this->db->prepare('
                INSERT INTO users 
                (user_id, username, coins, wallet_address, referrer_id, referral_code) 
                VALUES 
                (:user_id, :username, 10, NULL, NULL, NULL)
            ');
            $stmt->bindValue(':user_id', $userId, SQLITE3_INTEGER);
            $stmt->bindValue(':username', $username, SQLITE3_TEXT);
            
            if ($stmt->execute()) {
                // Возвращаем данные нового пользователя
                $this->sendResponse([
                    'exists' => true,
                    'user' => [
                        'user_id' => $userId,
                        'username' => $username,
                        'coins' => 10,
                        'wallet_address' => null,
                        'referrer_id' => null,
                        'referral_code' => null
                    ]
                ]);
            } else {
                $this->sendError('Failed to create user');
            }
        }
    } catch (Exception $e) {
        $this->sendError('Error checking user: ' . $e->getMessage());
    }
}

    public function updateCoins($userId, $coins) {
        try {
            // Сначала получаем текущее количество монет
            $stmt = $this->db->prepare('SELECT coins FROM users WHERE user_id = :user_id');
            $stmt->bindValue(':user_id', $userId, SQLITE3_INTEGER);
            $result = $stmt->execute();
            $user = $result->fetchArray(SQLITE3_ASSOC);
            
            if (!$user) {
                $this->sendError('User not found');
                return;
            }

            // Обновляем монеты
            $stmt = $this->db->prepare('
                UPDATE users 
                SET coins = :new_coins 
                WHERE user_id = :user_id
            ');
            
            $stmt->bindValue(':user_id', $userId, SQLITE3_INTEGER);
            $stmt->bindValue(':new_coins', $coins, SQLITE3_INTEGER);
            
            if ($stmt->execute()) {
                // Возвращаем обновленное количество монет
                $this->sendResponse([
                    'success' => true,
                    'coins' => $coins
                ]);
            } else {
                $this->sendError('Failed to update coins');
            }
        } catch (Exception $e) {
            $this->sendError('Error updating coins: ' . $e->getMessage());
        }
    }

    public function getLeaderboard() {
        try {
            $result = $this->db->query('
                SELECT user_id, username, coins 
                FROM users 
                ORDER BY coins DESC 
                LIMIT 999
            ');
            
            $leaderboard = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $leaderboard[] = $row;
            }
            
            $this->sendResponse([
                'success' => true,
                'leaderboard' => $leaderboard
            ]);
        } catch (Exception $e) {
            $this->sendError('Error fetching leaderboard: ' . $e->getMessage());
        }
    }

    public function getUserCoins($userId) {
        try {
            $stmt = $this->db->prepare('SELECT coins FROM users WHERE user_id = :user_id');
            $stmt->bindValue(':user_id', $userId, SQLITE3_INTEGER);
            $result = $stmt->execute();
            $user = $result->fetchArray(SQLITE3_ASSOC);
            
            if ($user) {
                $this->sendResponse([
                    'success' => true,
                    'coins' => $user['coins']
                ]);
            } else {
                $this->sendError('User not found');
            }
        } catch (Exception $e) {
            $this->sendError('Error getting user coins: ' . $e->getMessage());
        }
    }

    public function getTotalCoins() {
        try {
            $result = $this->db->query('SELECT SUM(coins) as total FROM users');
            $total = $result->fetchArray(SQLITE3_ASSOC);
            
            if ($total && isset($total['total'])) {
                $this->sendResponse([
                    'success' => true,
                    'total_coins' => $total['total']
                ]);
            } else {
                $this->sendResponse([
                    'success' => true,
                    'total_coins' => 0
                ]);
            }
        } catch (Exception $e) {
            $this->sendError('Error getting total coins: ' . $e->getMessage());
        }
    }

    public function getTimer() {
        try {
            $result = $this->db->query('SELECT end_time FROM timer WHERE id = 1');
            $timer = $result->fetchArray(SQLITE3_ASSOC);
            
            if ($timer) {
                $currentTime = time();
                $endTime = $timer['end_time'];
                $remainingTime = max(0, $endTime - $currentTime);
                
                // Конвертируем в дни, часы, минуты и секунды
                $days = floor($remainingTime / 86400);
                $hours = floor(($remainingTime % 86400) / 3600);
                $minutes = floor(($remainingTime % 3600) / 60);
                $seconds = $remainingTime % 60;
                
                $this->sendResponse([
                    'success' => true,
                    'timer' => [
                        'days' => str_pad($days, 2, '0', STR_PAD_LEFT),
                        'hours' => str_pad($hours, 2, '0', STR_PAD_LEFT),
                        'minutes' => str_pad($minutes, 2, '0', STR_PAD_LEFT),
                        'seconds' => str_pad($seconds, 2, '0', STR_PAD_LEFT)
                    ]
                ]);
            } else {
                $this->sendError('Timer not found');
            }
        } catch (Exception $e) {
            $this->sendError('Error getting timer: ' . $e->getMessage());
        }
    }
}

// Обработка запросов
$db = new DatabaseHandler();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $data = json_decode(file_get_contents('php://input'), true);
    
    switch ($_GET['action'] ?? '') {
        case 'check_user':
            if (isset($data['user_id'])) {
                $db->checkUser($data['user_id']);
            }
            break;
            
        case 'update_coins':
            if (isset($data['user_id']) && isset($data['coins'])) {
                $db->updateCoins($data['user_id'], $data['coins']);
            }
            break;

        case 'get_coins':
            if (isset($data['user_id'])) {
                $db->getUserCoins($data['user_id']);
            }
            break;
    }
} elseif ($_SERVER['REQUEST_METHOD'] === 'GET') {
    switch ($_GET['action'] ?? '') {
        case 'leaderboard':
            $db->getLeaderboard();
            break;
            
        case 'total_coins':
            $db->getTotalCoins();
            break;
            
        case 'timer':
            $db->getTimer();
            break;
    }
}

$db->sendError('Invalid request'); 
