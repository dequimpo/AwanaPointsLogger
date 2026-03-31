/**
 * Awana Points Logger - React Native/Expo App
 * MSAL Authentication with MS365 Integration
 */

import React, { useState, useEffect, useRef, Component } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Switch,
  SafeAreaView,
  ActivityIndicator,
  Alert,
  Platform,
  FlatList,
} from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useFonts } from 'expo-font';

// Authentication & API Services
import authService from './services/authService';
import apiClient from './services/apiClient';
import LoginScreen from './screens/LoginScreen';
import { appConfig } from './config/appConfig';

// API Configuration
const API_BASE_URL = appConfig.apiBaseUrl;

// Error Boundary
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error boundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.errorContainer}>
          <MaterialCommunityIcons name="alert-circle" size={48} color="#E74C3C" />
          <Text style={styles.errorText}>❌ Error</Text>
          <Text style={styles.errorDetail}>{this.state.error?.message}</Text>
        </View>
      );
    }

    return this.props.children;
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

const getAccessToken = async () => {
  try {
    return await authService.getAccessToken();
  } catch (error) {
    console.error('Failed to get access token:', error);
    throw error;
  }
};

// ============================================================================
// SCREEN 1: DATE & CLASS SELECTION
// ============================================================================
const DateClassSelectionScreen = ({ onNavigate, onSummary, onLogout, userName, onHelp }) => {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [selectedClass, setSelectedClass] = useState(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [apiStatus, setApiStatus] = useState(null);

  useEffect(() => {
    checkBackendConnection();
  }, []);

  const checkBackendConnection = async () => {
    try {
      const isHealthy = await apiClient.checkHealth();
      setApiStatus(isHealthy ? 'ok' : 'error');
    } catch (error) {
      console.error('Backend health check failed:', error);
      setApiStatus('error');
    }
  };

  const handleDateChange = (event, date) => {
    if (date) {
      const d = new Date(date);
      const day = d.getDay(); // 0 = Sunday, 1 = Monday, etc.
      const diff = day === 0 ? 0 : -day; // Days to subtract to get to Sunday
      const sunday = new Date(d);
      sunday.setDate(d.getDate() + diff);
      setSelectedDate(sunday);
    }
    if (Platform.OS !== 'web') {
      setShowDatePicker(false);
    }
  };

  const handleContinue = () => {
    if (!selectedClass) {
      Alert.alert('Selection Required', 'Please select a class (Journey_Boys, Journey_Girls, Trek, T&T, or Cubbies)');
      return;
    }
    
    // Internal API date format: YYYY-MM-DD
    const year = selectedDate.getFullYear();
    const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
    const day = String(selectedDate.getDate()).padStart(2, '0');
    const dateString = `${year}-${month}-${day}`;
    
    console.log(`📅 Sending to API - date: ${dateString}, class: ${selectedClass}`);
    
    onNavigate({
      date: dateString,
      class: selectedClass,
    });
  };

  const getDateString = () => {
    return selectedDate.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.screenContent}>
        <View style={styles.header}>
          <View style={styles.headerTopRow}>
            <View style={styles.headerLeftAction}>
              {onHelp ? (
                <TouchableOpacity style={styles.helpButton} onPress={onHelp} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                  <MaterialCommunityIcons name="help-circle-outline" size={22} color="#2C3E50" />
                </TouchableOpacity>
              ) : null}
            </View>
            <View style={styles.headerTitleSection} pointerEvents="none">
              <View style={styles.logoContainer}>
                <MaterialCommunityIcons name="scoreboard" size={40} color="#2C3E50" />
                <Text style={styles.logoText}>DBDNJ</Text>
              </View>
              <Text style={styles.title}>Awana Points Logger</Text>
            </View>
            <View style={styles.headerActions}>
              {onLogout ? (
                <TouchableOpacity style={styles.signOutButton} onPress={onLogout} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                  <MaterialCommunityIcons name="logout" size={16} color="#2C3E50" />
                  <Text style={styles.signOutButtonText}>Sign Out</Text>
                </TouchableOpacity>
              ) : null}
            </View>
          </View>
          
          <View style={styles.apiStatusContainer}>
            <MaterialCommunityIcons
              name={apiStatus === 'ok' ? 'cloud-check' : apiStatus === 'error' ? 'cloud-alert' : 'cloud-question'}
              size={16}
              color={apiStatus === 'ok' ? '#27AE60' : apiStatus === 'error' ? '#E74C3C' : '#F39C12'}
            />
            <Text style={[
              styles.apiStatusText,
              { color: apiStatus === 'ok' ? '#27AE60' : apiStatus === 'error' ? '#E74C3C' : '#F39C12' }
            ]}>
              {apiStatus === 'ok' ? 'API Connected' : apiStatus === 'error' ? 'API Offline' : 'Connecting...'}
            </Text>
          </View>

          <Text style={styles.subtitle}>Select Date & Class</Text>
          {userName ? <Text style={styles.signedInText}>Signed in: {userName}</Text> : null}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardLabel}>Sunday Date</Text>
          {Platform.OS === 'web' ? (
            <View style={styles.datePickerWebContainer}>
              <TouchableOpacity
                style={styles.dateNavButton}
                onPress={() => {
                  const newDate = new Date(selectedDate);
                  newDate.setDate(newDate.getDate() - 7);
                  const day = newDate.getDay();
                  const diff = day === 0 ? 0 : -day;
                  newDate.setDate(newDate.getDate() + diff);
                  setSelectedDate(newDate);
                }}
              >
                <MaterialCommunityIcons name="arrow-left" size={24} color="#FFF" />
              </TouchableOpacity>
              
              <View style={styles.dateDisplayContainer}>
                <MaterialCommunityIcons name="calendar" size={24} color="#3498DB" />
                <Text style={styles.dateDisplayText}>{getDateString()}</Text>
              </View>
              
              <TouchableOpacity
                style={styles.dateNavButton}
                onPress={() => {
                  const newDate = new Date(selectedDate);
                  newDate.setDate(newDate.getDate() + 7);
                  const day = newDate.getDay();
                  const diff = day === 0 ? 0 : -day;
                  newDate.setDate(newDate.getDate() + diff);
                  setSelectedDate(newDate);
                }}
              >
                <MaterialCommunityIcons name="arrow-right" size={24} color="#FFF" />
              </TouchableOpacity>
            </View>
          ) : (
            <>
              <TouchableOpacity
                style={styles.dateButton}
                onPress={() => setShowDatePicker(true)}
              >
                <MaterialCommunityIcons name="calendar" size={24} color="#3498DB" />
                <Text style={styles.dateButtonText}>{getDateString()}</Text>
              </TouchableOpacity>

              {showDatePicker && (
                <DateTimePicker
                  value={selectedDate}
                  mode="date"
                  onChange={handleDateChange}
                />
              )}
            </>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardLabel}>Class</Text>
          <View style={styles.classButtonsContainer}>
            {['Journey_Boys', 'Journey_Girls', 'Trek', 'T&T', 'Cubbies'].map((className) => (
              <TouchableOpacity
                key={className}
                style={[
                  styles.classButton,
                  selectedClass === className && styles.classButtonActive,
                ]}
                onPress={() => setSelectedClass(className)}
              >
                <MaterialCommunityIcons
                  name={
                    className === 'Journey_Boys' ? 'human-male' :
                    className === 'Journey_Girls' ? 'human-female' :
                    className === 'Trek' ? 'hiking' :
                    className === 'T&T' ? 'book-open-variant' :
                    'paw'  // Cubbies
                  }
                  size={32}
                  color={selectedClass === className ? '#FFF' : '#3498DB'}
                />
                <Text
                  style={[
                    styles.classButtonText,
                    selectedClass === className && styles.classButtonTextActive,
                  ]}
                >
                  {className}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <TouchableOpacity
          style={[styles.continueButton, !selectedClass && styles.continueButtonDisabled]}
          onPress={handleContinue}
          disabled={!selectedClass}
        >
          <Text style={styles.continueButtonText}>Continue to Logging</Text>
          <MaterialCommunityIcons name="arrow-right" size={20} color="#FFF" />
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.summaryButton}
          onPress={onSummary}
        >
          <MaterialCommunityIcons name="chart-box" size={20} color="#FFF" />
          <Text style={styles.summaryButtonText}>View Leaderboard</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

// ============================================================================
// TOGGLE FIELD COMPONENT (must be defined before StudentLoggingScreen)
// ============================================================================
const ToggleField = ({ label, value, onToggle, syncing }) => {
  const isOn = !!value;
  
  return (
    <View style={styles.toggleField}>
      <View style={styles.toggleButtonWrapper}>
        <TouchableOpacity
          onPress={onToggle}
          disabled={syncing}
          style={[
            styles.toggleButton,
            isOn ? styles.toggleButtonOn : styles.toggleButtonOff,
            syncing && styles.toggleButtonSyncing,
          ]}
        >
          <Text style={styles.toggleButtonText}>{isOn ? '✓' : ''}</Text>
        </TouchableOpacity>
        {syncing ? <View style={styles.toggleSyncDot} /> : null}
      </View>
      <Text style={styles.toggleLabel}>{label}</Text>
    </View>
  );
};

// ============================================================================
// SCREEN 2: STUDENT LOGGING LIST
// ============================================================================
const StudentLoggingScreen = ({ date, classValue, onBack }) => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState({});
  const [syncingRows, setSyncingRows] = useState({});
  const rosterCacheRef = useRef({});
  const rowLocksRef = useRef(new Set());

  const calculateStudentTotal = (student) => {
    if (!student) return 0;

    const basePoints = (
      (student.attendance || 0) +
      (student.bible || 0) +
      (student.bookAnswered || 0) +
      (student.memoryVerse || 0) +
      (student.participation || 0)
    ) * 10;

    const bonusPoints =
      (student.bonus1Baf1 || 0) * 30 +
      (student.bonus2Baf2 || 0) * 20 +
      (student.bonus3Participation || 0) * 20;

    return basePoints + bonusPoints;
  };

  useEffect(() => {
    fetchStudents();
  }, [date, classValue]);

  const fetchStudents = async () => {
    try {
      setLoading(true);
      const token = await getAccessToken();

      // 1) Ensure all class students have a PointsLog row for this Sunday.
      const bootstrapResponse = await fetch(`${API_BASE_URL}/sheets/PointsLogSheet/bootstrap`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          date,
          class_name: classValue,
        }),
      });

      if (!bootstrapResponse.ok) {
        // Backward compatibility: if new bootstrap route is missing on running backend,
        // fall back to legacy auto-populate endpoint instead of blocking page load.
        if (bootstrapResponse.status === 404) {
          console.warn('⚠️ /sheets/PointsLogSheet/bootstrap not found; falling back to /sheets/PointsLog/auto-populate');
          const fallbackResponse = await fetch(`${API_BASE_URL}/sheets/PointsLog/auto-populate`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              date,
              class_name: classValue,
            }),
          });

          if (!fallbackResponse.ok) {
            const fallbackError = await fallbackResponse.text();
            console.warn(`⚠️ Bootstrap fallback failed: HTTP ${fallbackResponse.status}: ${fallbackError}`);
          } else {
            await fallbackResponse.json();
          }
        } else {
          const bootstrapError = await bootstrapResponse.text();
          console.warn(`⚠️ Bootstrap failed: HTTP ${bootstrapResponse.status}: ${bootstrapError}`);
        }
      } else {
        await bootstrapResponse.json();
      }

      const rosterResponse = await fetch(`${API_BASE_URL}/sheets/Students`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!rosterResponse.ok) {
        throw new Error(`HTTP ${rosterResponse.status}: ${rosterResponse.statusText}`);
      }

      const rosterData = await rosterResponse.json();
      const rosterRows = (rosterData.data || []).filter(
        (row) => Array.isArray(row) && row.length >= 3 && String(row[0] || '').trim() !== ''
      );
      rosterCacheRef.current = rosterRows.reduce((acc, row) => {
        const cacheKey = `${String(row[2]).trim()}::${String(row[1]).trim()}`;
        acc[cacheKey] = String(row[0]).trim();
        return acc;
      }, {});
      
      // 2) Fetch only this date+class rows (already normalized on backend).
      const response = await fetch(
        `${API_BASE_URL}/sheets/PointsLogSheet?date_value=${encodeURIComponent(date)}&class_name=${encodeURIComponent(classValue)}`,
        {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const rows = (data.data || []).filter(
        (row) => Array.isArray(row) && row.length >= 3 && String(row[0] || '').trim() !== ''
      );

      const normalizeDateString = (value) => {
        if (typeof value === 'string') return value;
        if (typeof value === 'number') {
          const d = new Date((value - 25569) * 86400 * 1000);
          return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`;
        }
        return String(value || '');
      };

      // Parse and filter students by date and class
      let matchCount = 0;
      
      const parsedStudents = rows
        .filter((row) => {
          if (!row || row.length < 3) {
            return false;
          }
          
          const rowDate = normalizeDateString(row[0]);
          const rowClass = row[1];
          
          const dateMatch = rowDate === String(date);
          const classMatch = String(rowClass) === String(classValue);
          
          if (dateMatch && classMatch) {
            matchCount++;
          }
          
          return dateMatch && classMatch;
        })
        .map((row, idx) => {
          const rowDate = normalizeDateString(row[0]);
          const rowClass = String(row[1]);
          const studentName = String(row[2]);
          const studentId = rosterCacheRef.current[`${rowClass}::${studentName}`] || null;
          const student = {
            rowKey: `${rowDate}-${rowClass}-${studentName}-${idx}`,
            studentId,
            name: studentName,
            attendance: row[3] ? 1 : 0,
            bible: row[4] ? 1 : 0,
            bookAnswered: row[5] ? 1 : 0,
            memoryVerse: row[6] ? 1 : 0,
            participation: row[7] ? 1 : 0,
            bonus1Baf1: row[8] ? 1 : 0,
            bonus2Baf2: row[9] ? 1 : 0,
            bonus3Participation: row[10] ? 1 : 0,
            totalPoints: row[11] || 0,
          };
          return student;
        });

      setStudents(parsedStudents);
    } catch (error) {
      console.error('Fetch error:', error);
      Alert.alert('Error', 'Failed to fetch students: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const updateToggle = async (studentRowKey, studentName, field, newValue) => {
    if (rowLocksRef.current.has(studentRowKey)) {
      return;
    }

    rowLocksRef.current.add(studentRowKey);
    setSyncingRows((prev) => ({ ...prev, [studentRowKey]: true }));

    const syncKey = `${studentRowKey}-${field}`;
    setSyncing((prev) => ({ ...prev, [syncKey]: true }));
    let currentStudent = null;

    try {
      const token = await getAccessToken();
      
      const fieldMap = {
        attendance: 'attendance',
        bible: 'bible',
        bookAnswered: 'book_answered',
        memoryVerse: 'memory_verse',
        participation: 'participation',
        bonus1Baf1: 'bonus1_baf_1',
        bonus2Baf2: 'bonus2_baf_2',
        bonus3Participation: 'bonus3_participation',
      };

      const backendField = fieldMap[field] || field.replace(/([A-Z])/g, '_$1').toLowerCase();

      currentStudent = students.find((s) => s.rowKey === studentRowKey);

      const optimisticStudent = {
        ...currentStudent,
        [field]: newValue ? 1 : 0,
      };
      const optimisticTotal = calculateStudentTotal(optimisticStudent);

      setStudents((prevStudents) =>
        prevStudents.map((student) =>
          student.rowKey === studentRowKey
            ? { ...optimisticStudent, totalPoints: optimisticTotal }
            : student
        )
      );

      const payload = {
        date,
        class_name: classValue,
        student_name: studentName,
        student_id: currentStudent?.studentId || undefined,
        [backendField]: newValue ? 1 : 0,
      };

      const response = await fetch(`${API_BASE_URL}/sheets/PointsLogSheet/update`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const responseData = await response.json();
      const serverTotal = Number(responseData?.total_points ?? 0);

      setStudents((prevStudents) => {
        return prevStudents.map((student) =>
          student.rowKey === studentRowKey
            ? { ...student, [field]: newValue ? 1 : 0, totalPoints: serverTotal }
            : student
        );
      });
    } catch (error) {
      console.error('Update error:', error);
      // Best-effort rollback to previous snapshot if server update fails.
      setStudents((prevStudents) =>
        prevStudents.map((student) =>
          student.rowKey === studentRowKey && currentStudent
            ? currentStudent
            : student
        )
      );
      Alert.alert('Sync Error', 'Could not sync: ' + error.message);
    } finally {
      rowLocksRef.current.delete(studentRowKey);
      setSyncingRows((prev) => ({ ...prev, [studentRowKey]: false }));
      setSyncing((prev) => ({ ...prev, [syncKey]: false }));
    }
  };

  const renderStudentRow = ({ item: student }) => {
    const rowSyncing = !!syncingRows[student.rowKey];

    return (
    <View style={styles.studentRow}>
      <Text style={styles.studentName}>{student.name}</Text>

      <View style={styles.togglesContainer}>
        <ToggleField label="Att" value={student.attendance} onToggle={() => updateToggle(student.rowKey, student.name, 'attendance', !student.attendance)} syncing={rowSyncing || syncing[`${student.rowKey}-attendance`]} />
        <ToggleField label="Bib" value={student.bible} onToggle={() => updateToggle(student.rowKey, student.name, 'bible', !student.bible)} syncing={rowSyncing || syncing[`${student.rowKey}-bible`]} />
        <ToggleField label="BA" value={student.bookAnswered} onToggle={() => updateToggle(student.rowKey, student.name, 'bookAnswered', !student.bookAnswered)} syncing={rowSyncing || syncing[`${student.rowKey}-bookAnswered`]} />
        <ToggleField label="MV" value={student.memoryVerse} onToggle={() => updateToggle(student.rowKey, student.name, 'memoryVerse', !student.memoryVerse)} syncing={rowSyncing || syncing[`${student.rowKey}-memoryVerse`]} />
        <ToggleField label="Part" value={student.participation} onToggle={() => updateToggle(student.rowKey, student.name, 'participation', !student.participation)} syncing={rowSyncing || syncing[`${student.rowKey}-participation`]} />
        <ToggleField label="B1" value={student.bonus1Baf1} onToggle={() => updateToggle(student.rowKey, student.name, 'bonus1Baf1', !student.bonus1Baf1)} syncing={rowSyncing || syncing[`${student.rowKey}-bonus1Baf1`]} />
        <ToggleField label="B2" value={student.bonus2Baf2} onToggle={() => updateToggle(student.rowKey, student.name, 'bonus2Baf2', !student.bonus2Baf2)} syncing={rowSyncing || syncing[`${student.rowKey}-bonus2Baf2`]} />
        <ToggleField label="B3" value={student.bonus3Participation} onToggle={() => updateToggle(student.rowKey, student.name, 'bonus3Participation', !student.bonus3Participation)} syncing={rowSyncing || syncing[`${student.rowKey}-bonus3Participation`]} />
      </View>

      <Text style={styles.totalPoints}>{student.totalPoints}</Text>
    </View>
  );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3498DB" />
        <Text style={styles.loadingText}>Loading students...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.loggingHeader}>
        <TouchableOpacity onPress={onBack}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#2C3E50" />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.headerDate}>{date}</Text>
          <Text style={styles.headerClass}>{classValue} Class</Text>
        </View>
        <View style={{ width: 24 }} />
      </View>

      <View style={styles.headerRow}>
        <Text style={styles.headerName}>Name</Text>
        <View style={styles.headerToggles}>
          <Text style={styles.headerToggle}>Att</Text>
          <Text style={styles.headerToggle}>Bib</Text>
          <Text style={styles.headerToggle}>BA</Text>
          <Text style={styles.headerToggle}>MV</Text>
          <Text style={styles.headerToggle}>Part</Text>
          <Text style={styles.headerToggle}>B1</Text>
          <Text style={styles.headerToggle}>B2</Text>
          <Text style={styles.headerToggle}>B3</Text>
        </View>
        <Text style={styles.headerTotal}>Pts</Text>
      </View>

      <View style={{ padding: 8, backgroundColor: '#F0F0F0' }}>
        <Text style={{ fontSize: 12, color: '#666' }}>📊 Students loaded: {students.length}</Text>
      </View>

      {students.length === 0 && !loading ? (
        <View style={styles.emptyState}>
          <MaterialCommunityIcons name="inbox-multiple" size={48} color="#BDC3C7" />
          <Text style={styles.emptyStateText}>No students for this class</Text>
        </View>
      ) : null}

      <ScrollView style={styles.studentListContainer}>
        {students.map((student, index) => {
          return <View key={student.rowKey || `${date}-${classValue}-${student.name}-${index}`}>{renderStudentRow({ item: student })}</View>;
        })}
      </ScrollView>
    </SafeAreaView>
  );
};

// ============================================================================
// SCREEN 3: STUDENT SUMMARY (ACCUMULATED POINTS)
// ============================================================================
const StudentSummaryScreen = ({ onBack }) => {
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedClass, setSelectedClass] = useState(null);
  const [allClasses, setAllClasses] = useState([]);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      const token = await getAccessToken();
      
      const response = await fetch(`${API_BASE_URL}/sheets/student-summary`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('📊 Summary data:', JSON.stringify(data.summary, null, 2));
      
      setSummary(data.summary || {});
      const classes = Object.keys(data.summary || {}).sort();
      setAllClasses(classes);
      if (classes.length > 0) {
        setSelectedClass(classes[0]);
      }
    } catch (error) {
      console.error('Fetch error:', error);
      Alert.alert('Error', 'Failed to fetch summary: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const getClassIcon = (className) => {
    switch (className) {
      case 'Journey_Boys':
        return 'human-male';
      case 'Journey_Girls':
        return 'human-female';
      case 'Trek':
        return 'hiking';
      case 'T&T':
        return 'book-open-variant';
      case 'Cubbies':
        return 'paw';
      default:
        return 'account';
    }
  };

  const getRankMedal = (rank) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `${rank}.`;
  };

  const renderSummaryRow = (student, rank) => (
    <View key={student.name} style={styles.summaryRow}>
      <Text style={styles.summaryRank}>{getRankMedal(rank)}</Text>
      <Text style={styles.summaryName}>{student.name}</Text>
      <View style={styles.summaryPointsBadge}>
        <Text style={styles.summaryPoints}>{student.total_points}</Text>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3498DB" />
        <Text style={styles.loadingText}>Loading summary...</Text>
      </View>
    );
  }

  const currentClassData = summary[selectedClass] || [];
  const totalPoints = currentClassData.reduce((sum, s) => sum + s.total_points, 0);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.summaryHeader}>
        <TouchableOpacity onPress={onBack}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#2C3E50" />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.summaryHeaderTitle}>Accumulated Points</Text>
          <Text style={styles.summaryHeaderSubtitle}>All-Time Leaderboard</Text>
        </View>
        <View style={{ width: 24 }} />
      </View>

      {/* Class Filter Buttons */}
      <View style={styles.classFilterContainer}>
        <View style={[styles.classFilterContent, styles.classButtonsContainer]}>
          {allClasses.filter(c => ['Journey_Boys', 'Journey_Girls', 'Trek', 'T&T', 'Cubbies'].includes(c)).map((className) => (
            <TouchableOpacity
              key={className}
              style={[
                styles.classButton,
                selectedClass === className && styles.classButtonActive,
              ]}
              onPress={() => setSelectedClass(className)}
            >
              <MaterialCommunityIcons
                name={getClassIcon(className)}
                size={32}
                color={selectedClass === className ? '#FFF' : '#3498DB'}
              />
              <Text
                style={[
                  styles.classButtonText,
                  selectedClass === className && styles.classButtonTextActive,
                ]}
              >
                {className}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Summary Stats */}
      <View style={styles.summaryStatsContainer}>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>Students</Text>
          <Text style={styles.statValue}>{currentClassData.length}</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>Total Points</Text>
          <Text style={styles.statValue}>{totalPoints}</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>Average</Text>
          <Text style={styles.statValue}>
            {currentClassData.length > 0 ? Math.round(totalPoints / currentClassData.length) : 0}
          </Text>
        </View>
      </View>

      {/* Student Rankings */}
      {currentClassData.length === 0 ? (
        <View style={styles.emptyState}>
          <MaterialCommunityIcons name="inbox-multiple" size={48} color="#BDC3C7" />
          <Text style={styles.emptyStateText}>No data for {selectedClass}</Text>
        </View>
      ) : (
        <ScrollView style={styles.summaryListContainer}>
          {currentClassData.map((student, rank) => renderSummaryRow(student, rank + 1))}
        </ScrollView>
      )}
    </SafeAreaView>
  );
};

// ============================================================================
// SCREEN 4: HELP SCREEN
// ============================================================================
const HelpScreen = ({ onBack }) => {
  const sections = [
    {
      icon: 'information-outline',
      title: 'About This App',
      color: '#3498DB',
      content: 'The DBDNJ Awana Points Logger helps leaders quickly record weekly participation and achievement points for each class, then view a running leaderboard across the season.',
    },
    {
      icon: 'numeric-1-circle',
      title: 'Step 1 — Pick a Date & Class',
      color: '#27AE60',
      items: [
        'The date selector always snaps to the Sunday of the chosen week.',
        'Use the ◀ ▶ arrows (web) or tap the date (mobile) to change weeks.',
        'Tap one of the five class tiles: Journey Boys, Journey Girls, Trek, T&T, or Cubbies.',
        'Press "Continue to Logging" to open that class\'s roster.',
      ],
    },
    {
      icon: 'numeric-2-circle',
      title: 'Step 2 — Log Points',
      color: '#E67E22',
      items: [
        'Each row is one student. Tap a checkbox to toggle it on/off.',
        'Changes sync to the server instantly (blue dot = syncing).',
        'The "Pts" column on the right shows each student\'s total for the session.',
      ],
    },
    {
      icon: 'checkbox-marked-outline',
      title: 'Point Categories',
      color: '#8E44AD',
      table: [
        { abbr: 'Att', label: 'Attendance', pts: '10' },
        { abbr: 'Bib', label: 'Bible Brought', pts: '10' },
        { abbr: 'BA',  label: 'Book Answered', pts: '10' },
        { abbr: 'MV',  label: 'Memory Verse', pts: '10' },
        { abbr: 'Part',label: 'Participation', pts: '10' },
        { abbr: 'B1',  label: 'Bonus – BAF 1', pts: '30' },
        { abbr: 'B2',  label: 'Bonus – BAF 2', pts: '20' },
        { abbr: 'B3',  label: 'Bonus – Participation', pts: '20' },
      ],
    },
    {
      icon: 'numeric-3-circle',
      title: 'Step 3 — View the Leaderboard',
      color: '#2980B9',
      items: [
        'Tap "View Leaderboard" on the home screen.',
        'Switch between classes using the class buttons at the top.',
        'Students are ranked by accumulated points across all recorded Sundays.',
        '🥇 🥈 🥉 medals highlight the top three.',
      ],
    },
    {
      icon: 'cloud-check-outline',
      title: 'API Status Indicator',
      color: '#16A085',
      items: [
        '🟢 Green "API Connected" — the backend is reachable and data will save.',
        '🔴 Red "API Offline" — the backend is down; toggles will fail to sync.',
        'If offline, ask your system administrator to restart the server.',
      ],
    },
    {
      icon: 'lightbulb-outline',
      title: 'Tips',
      color: '#F39C12',
      items: [
        'You can re-open a past Sunday and change any toggles at any time.',
        'Each session is tied to a specific date + class combination.',
        'Totals on the leaderboard update as soon as you tap a checkbox.',
      ],
    },
    {
      icon: 'cross',
      title: 'The Awana Theme',
      color: '#2C3E50',
      content: 'At the heart of everything we do in Jr. Sunday School is a commitment to growing in faith and understanding. The name Awana is an acronym derived from the first letters of our theme verse: Approved Workmen Are Not Ashamed.',
      quoteTitle: 'Our Theme Verse',
      quote: '"Do your best to present yourself to God as one approved, a worker who does not need to be ashamed and who correctly handles the word of truth."',
      quoteRef: '2 Timothy 2:15 (NIV)',
      items: [
        'Be Diligent: To "do your best" in studying and applying God\'s Word every Sunday.',
        'Be Purposeful: To live a life that seeks God\'s approval above all else, even at a young age.',
        'Be Confident: To handle the Truth with integrity so that we may stand before Him without shame.',
        'Whether we are gathering for a group lesson, working through our handbooks, or sharing in fellowship, we strive to build a foundation of biblical wisdom in Jr. Sunday School that lasts a lifetime.',
      ],
    },
    {
      icon: 'help-circle-outline',
      title: 'Questions?',
      color: '#1F618D',
      content: 'If you have any questions about our Jr. Sunday School program or the Awana curriculum, please reach out to Tita Monette or T2D.',
    },
  ];

  const renderSection = (section, idx) => (
    <View key={idx} style={styles.helpSection}>
      <View style={styles.helpSectionHeader}>
        <View style={[styles.helpIconCircle, { backgroundColor: section.color + '20' }]}>
          <MaterialCommunityIcons name={section.icon} size={22} color={section.color} />
        </View>
        <Text style={[styles.helpSectionTitle, { color: section.color }]}>{section.title}</Text>
      </View>

      {section.content ? (
        <Text style={styles.helpParagraph}>{section.content}</Text>
      ) : null}

      {section.quote ? (
        <View style={styles.helpQuoteBox}>
          {section.quoteTitle ? <Text style={styles.helpQuoteTitle}>{section.quoteTitle}</Text> : null}
          <Text style={styles.helpQuoteText}>{section.quote}</Text>
          {section.quoteRef ? <Text style={styles.helpQuoteRef}>- {section.quoteRef}</Text> : null}
        </View>
      ) : null}

      {section.items ? section.items.map((item, i) => (
        <View key={i} style={styles.helpBulletRow}>
          <Text style={[styles.helpBulletDot, { color: section.color }]}>•</Text>
          <Text style={styles.helpBulletText}>{item}</Text>
        </View>
      )) : null}

      {section.table ? (
        <View style={styles.helpTable}>
          <View style={styles.helpTableHeaderRow}>
            <Text style={[styles.helpTableHeader, { flex: 0.8 }]}>Abbr</Text>
            <Text style={[styles.helpTableHeader, { flex: 2 }]}>Meaning</Text>
            <Text style={[styles.helpTableHeader, { flex: 0.7, textAlign: 'right' }]}>Pts</Text>
          </View>
          {section.table.map((row, i) => (
            <View key={i} style={[styles.helpTableRow, i % 2 === 1 && styles.helpTableRowAlt]}>
              <Text style={[styles.helpTableAbbr, { flex: 0.8 }]}>{row.abbr}</Text>
              <Text style={[styles.helpTableCell, { flex: 2 }]}>{row.label}</Text>
              <Text style={[styles.helpTablePts, { flex: 0.7 }]}>{row.pts}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.summaryHeader}>
        <TouchableOpacity onPress={onBack}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#2C3E50" />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.summaryHeaderTitle}>How to Use</Text>
          <Text style={styles.summaryHeaderSubtitle}>DBDNJ Awana Points Logger</Text>
        </View>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.helpScrollContent}>
        {sections.map(renderSection)}

        <View style={styles.helpFooter}>
          <MaterialCommunityIcons name="heart-outline" size={18} color="#BDC3C7" />
          <Text style={styles.helpFooterText}>DBDNJ Awana Ministry</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

// ============================================================================
// MAIN APP COMPONENT
// ============================================================================
function MainApp() {
  const [currentScreen, setCurrentScreen] = useState('selection');
  const [selectionData, setSelectionData] = useState({});
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userProfile, setUserProfile] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      const authenticated = await authService.initialize();
      if (authenticated) {
        const profile = await authService.getUserProfile();
        setUserProfile(profile);
        setIsAuthenticated(true);
      }
    } catch (error) {
      console.error('Auth initialization error:', error);
    } finally {
      setIsInitializing(false);
    }
  };

  const handleLoginSuccess = (profile) => {
    setUserProfile(profile);
    setIsAuthenticated(true);
    setCurrentScreen('selection');
  };

  const performLogout = async () => {
    try {
      await authService.logout();
      setIsAuthenticated(false);
      setUserProfile(null);
      setCurrentScreen('selection');
    } catch (error) {
      console.error('Logout error:', error);
      Alert.alert('Error', 'Failed to sign out');
    }
  };

  const handleLogout = async () => {
    if (Platform.OS === 'web') {
      const confirmed = typeof window !== 'undefined'
        ? window.confirm('Are you sure you want to sign out?')
        : true;
      if (confirmed) {
        await performLogout();
      }
      return;
    }

    Alert.alert('Confirm Logout', 'Are you sure you want to sign out?', [
      {
        text: 'Cancel',
        style: 'cancel',
      },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: performLogout,
      },
    ]);
  };

  const handleNavigateToLogging = (data) => {
    setSelectionData(data);
    setCurrentScreen('logging');
  };

  const handleNavigateToSummary = () => {
    setCurrentScreen('summary');
  };

  const handleBackToSelection = () => {
    setCurrentScreen('selection');
  };

  const handleNavigateToHelp = () => {
    setCurrentScreen('help');
  };

  // Show loading screen while initializing
  if (isInitializing) {
    return (
      <View style={[styles.appContainer, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color="#0078D4" />
        <Text style={{ marginTop: 16, color: '#666' }}>Initializing...</Text>
      </View>
    );
  }

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <View style={styles.appContainer}>
      {currentScreen === 'selection' ? (
        <DateClassSelectionScreen
          onNavigate={handleNavigateToLogging}
          onSummary={handleNavigateToSummary}
          onLogout={handleLogout}
          userName={userProfile?.displayName || 'User'}
          onHelp={handleNavigateToHelp}
        />
      ) : currentScreen === 'logging' ? (
        <StudentLoggingScreen
          date={selectionData.date}
          classValue={selectionData.class}
          onBack={handleBackToSelection}
        />
      ) : currentScreen === 'help' ? (
        <HelpScreen onBack={handleBackToSelection} />
      ) : (
        <StudentSummaryScreen onBack={handleBackToSelection} />
      )}
    </View>
  );
}



export default function App() {
  const [iconsLoaded] = useFonts(MaterialCommunityIcons.font);

  if (!iconsLoaded) {
    return (
      <View style={[styles.appContainer, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color="#0078D4" />
        <Text style={{ marginTop: 16, color: '#666' }}>Loading assets...</Text>
      </View>
    );
  }

  return (
    <ErrorBoundary>
      <MainApp />
    </ErrorBoundary>
  );
}

// ============================================================================
// STYLES
// ============================================================================
const styles = StyleSheet.create({
  appContainer: {
    flex: 1,
    backgroundColor: '#F5F6FA',
  },
  container: {
    flex: 1,
    backgroundColor: '#F5F6FA',
  },
  screenContent: {
    paddingHorizontal: 16,
    paddingVertical: 24,
  },

  // Header
  header: {
    marginBottom: 32,
  },
  headerTopRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'flex-start',
    marginBottom: 12,
    position: 'relative',
    minHeight: 40,
  },
  headerLeftAction: {
    width: 110,
    alignItems: 'flex-start',
    position: 'absolute',
    left: 0,
    top: 0,
    zIndex: 2,
    elevation: 2,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    width: 110,
    position: 'absolute',
    right: 0,
    top: 0,
    zIndex: 2,
    elevation: 2,
  },
  headerTitleSection: {
    alignItems: 'center',
    flex: 1,
    marginTop: 8,
  },
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  logoText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginLeft: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginTop: 12,
  },
  subtitle: {
    fontSize: 14,
    color: '#7F8C8D',
    marginTop: 12,
    textAlign: 'center',
  },
  signedInText: {
    fontSize: 12,
    color: '#2C3E50',
    marginTop: 8,
    textAlign: 'center',
  },
  signOutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ECF0F1',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  signOutButtonText: {
    marginLeft: 6,
    fontSize: 12,
    fontWeight: '600',
    color: '#2C3E50',
  },
  apiStatusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
    marginBottom: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#F5F6FA',
    borderRadius: 6,
  },
  apiStatusText: {
    fontSize: 12,
    fontWeight: '500',
    marginLeft: 6,
  },

  // Cards
  card: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2C3E50',
    marginBottom: 12,
  },

  // Date
  dateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#EBF5FB',
    borderRadius: 8,
  },
  dateButtonText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#3498DB',
    marginLeft: 12,
  },

  // Web Date Picker
  datePickerWebContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#EBF5FB',
    borderRadius: 8,
    gap: 12,
  },
  dateNavButton: {
    padding: 8,
    backgroundColor: '#3498DB',
    borderRadius: 4,
  },
  dateDisplayContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#FFF',
    borderRadius: 4,
  },
  dateDisplayText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#2C3E50',
    marginLeft: 8,
  },

  // Class
  classButtonsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  classButton: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 16,
    backgroundColor: '#F0F0F0',
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#E0E0E0',
  },
  classButtonActive: {
    backgroundColor: '#3498DB',
    borderColor: '#3498DB',
  },
  classButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#3498DB',
    marginTop: 8,
  },
  classButtonTextActive: {
    color: '#FFF',
  },

  // Button
  continueButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    backgroundColor: '#3498DB',
    borderRadius: 8,
    marginTop: 24,
  },
  continueButtonDisabled: {
    backgroundColor: '#BDC3C7',
  },
  continueButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFF',
    marginRight: 8,
  },

  // Student List Container
  studentListContainer: {
    flex: 1,
    backgroundColor: '#F5F6FA',
  },

  emptyStateContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },

  // Error
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#ffcccc',
    paddingHorizontal: 20,
  },
  errorText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#cc0000',
    marginTop: 12,
  },
  errorDetail: {
    fontSize: 14,
    color: '#cc0000',
    marginTop: 8,
    textAlign: 'center',
  },

  // Coming Soon
  comingSoonText: {
    flex: 1,
    textAlignVertical: 'center',
    textAlign: 'center',
    fontSize: 16,
    color: '#7F8C8D',
  },

  // Logging Screen
  loggingHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  headerInfo: {
    alignItems: 'center',
  },
  headerDate: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2C3E50',
  },
  headerClass: {
    fontSize: 12,
    color: '#7F8C8D',
    marginTop: 2,
  },

  // Column Headers
  headerRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#ECF0F1',
    borderBottomWidth: 1,
    borderBottomColor: '#BDC3C7',
  },
  headerName: {
    flex: 2,
    fontSize: 11,
    fontWeight: '600',
    color: '#2C3E50',
  },
  headerToggles: {
    flex: 3,
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  headerToggle: {
    fontSize: 10,
    fontWeight: '600',
    color: '#2C3E50',
  },
  headerTotal: {
    flex: 0.5,
    fontSize: 11,
    fontWeight: '600',
    color: '#2C3E50',
    textAlign: 'center',
  },

  // Student Row
  studentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  studentName: {
    flex: 2,
    fontSize: 12,
    fontWeight: '500',
    color: '#2C3E50',
  },
  togglesContainer: {
    flex: 3,
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  toggleField: {
    alignItems: 'center',
    minWidth: 36,
  },
  toggleButtonWrapper: {
    position: 'relative',
    width: 28,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  toggleButton: {
    width: 28,
    height: 28,
    borderRadius: 6,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  toggleButtonOn: {
    backgroundColor: '#27AE60',
    borderColor: '#27AE60',
  },
  toggleButtonOff: {
    backgroundColor: '#FFF',
    borderColor: '#BDC3C7',
  },
  toggleButtonSyncing: {
    opacity: 0.7,
  },
  toggleButtonText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '700',
  },
  toggleSyncDot: {
    position: 'absolute',
    top: -2,
    right: -2,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#3498DB',
    borderWidth: 1,
    borderColor: '#FFF',
  },
  toggle: {
    transform: [{ scaleX: 0.8 }, { scaleY: 0.8 }],
  },
  toggleLabel: {
    fontSize: 9,
    color: '#7F8C8D',
    marginTop: 2,
  },
  totalPoints: {
    flex: 0.5,
    fontSize: 12,
    fontWeight: '600',
    color: '#27AE60',
    textAlign: 'center',
  },

  // Loading State
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F6FA',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: '#7F8C8D',
  },

  // Empty State
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyStateText: {
    fontSize: 14,
    color: '#BDC3C7',
    marginTop: 12,
  },

  // Summary Button
  summaryButton: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
    backgroundColor: '#3498DB',
    borderRadius: 8,
    marginTop: 12,
    marginBottom: 24,
  },
  summaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFF',
    marginLeft: 8,
  },

  // Summary Screen Styles
  summaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 16,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#ECF0F1',
  },
  summaryHeaderTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2C3E50',
  },
  summaryHeaderSubtitle: {
    fontSize: 12,
    color: '#7F8C8D',
    marginTop: 4,
  },

  // Class Filter
  classFilterContainer: {
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#ECF0F1',
  },
  classFilterContent: {
    paddingHorizontal: 12,
    paddingVertical: 12,
    gap: 12,
  },
  classFilterButton: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    width: 104,
    minHeight: 88,
    paddingHorizontal: 12,
    paddingVertical: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#E0E0E0',
    backgroundColor: '#F0F0F0',
  },
  classFilterButtonActive: {
    backgroundColor: '#3498DB',
    borderColor: '#3498DB',
  },
  classFilterButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#3498DB',
    marginTop: 8,
    textAlign: 'center',
    width: '100%',
  },
  classFilterButtonTextActive: {
    color: '#FFF',
  },

  // Summary Stats
  summaryStatsContainer: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 16,
    backgroundColor: '#F5F6FA',
  },
  statBox: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: '#FFF',
    paddingVertical: 12,
    marginHorizontal: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ECF0F1',
  },
  statLabel: {
    fontSize: 11,
    color: '#7F8C8D',
    fontWeight: '500',
  },
  statValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#3498DB',
    marginTop: 4,
  },

  // Summary Row
  summaryListContainer: {
    flex: 1,
    backgroundColor: '#F5F6FA',
    paddingHorizontal: 8,
    paddingTop: 8,
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginVertical: 4,
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#3498DB',
  },
  summaryRank: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2C3E50',
    width: 30,
  },
  summaryName: {
    flex: 1,
    fontSize: 14,
    fontWeight: '500',
    color: '#2C3E50',
    marginLeft: 8,
  },
  summaryPointsBadge: {
    backgroundColor: '#3498DB',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  summaryPoints: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#FFF',
  },

  // Help Button (in header)
  helpButton: {
    padding: 4,
    borderRadius: 6,
    backgroundColor: '#ECF0F1',
  },

  // Help Screen
  helpScrollContent: {
    paddingHorizontal: 16,
    paddingVertical: 20,
    paddingBottom: 40,
  },
  helpSection: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.07,
    shadowRadius: 3,
    elevation: 2,
  },
  helpSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  helpIconCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  helpSectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    flex: 1,
  },
  helpParagraph: {
    fontSize: 14,
    color: '#555',
    lineHeight: 22,
  },
  helpQuoteBox: {
    marginTop: 12,
    marginBottom: 4,
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#F7F9FB',
    borderLeftWidth: 4,
    borderLeftColor: '#2C3E50',
  },
  helpQuoteTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#2C3E50',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  helpQuoteText: {
    fontSize: 14,
    color: '#2C3E50',
    lineHeight: 22,
    fontStyle: 'italic',
  },
  helpQuoteRef: {
    marginTop: 8,
    fontSize: 12,
    color: '#5D6D7E',
    fontWeight: '600',
  },
  helpBulletRow: {
    flexDirection: 'row',
    marginTop: 6,
  },
  helpBulletDot: {
    fontSize: 16,
    marginRight: 8,
    lineHeight: 22,
  },
  helpBulletText: {
    flex: 1,
    fontSize: 14,
    color: '#555',
    lineHeight: 22,
  },
  helpTable: {
    borderRadius: 8,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  helpTableHeaderRow: {
    flexDirection: 'row',
    backgroundColor: '#ECF0F1',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  helpTableHeader: {
    fontSize: 12,
    fontWeight: '700',
    color: '#2C3E50',
  },
  helpTableRow: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#FFF',
  },
  helpTableRowAlt: {
    backgroundColor: '#F8F9FA',
  },
  helpTableAbbr: {
    fontSize: 13,
    fontWeight: '600',
    color: '#3498DB',
  },
  helpTableCell: {
    fontSize: 13,
    color: '#444',
  },
  helpTablePts: {
    fontSize: 13,
    fontWeight: '600',
    color: '#27AE60',
    textAlign: 'right',
  },
  helpFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
    paddingVertical: 16,
    gap: 6,
  },
  helpFooterText: {
    fontSize: 12,
    color: '#BDC3C7',
    marginLeft: 6,
  },
});

