using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Runtime.InteropServices;

namespace USB2CAN
{



    public partial class Form1 : Form
    {


        class CanWrap
        {
            #region Delegates
            /// Error Codes
            public SortedDictionary<int, string> error_codes = new SortedDictionary<int, string>() {
                {   0  ,   "CANAL_ERROR_SUCCESS"           },  // All is OK
                {   1  ,   "CANAL_ERROR_BAUDRATE"          },  // Baudrate error
                {   2  ,   "CANAL_ERROR_BUS_OFF"           },  // Bus off error
                {   3  ,   "CANAL_ERROR_BUS_PASSIVE"       },  // Bus Passive error
                {   4  ,   "CANAL_ERROR_BUS_WARNING"       },  // Bus warning error
                {   5  ,   "CANAL_ERROR_CAN_ID"            },  // Invalid CAN ID
                {   6  ,   "CANAL_ERROR_CAN_MESSAGE"       },  // Invalid CAN message
                {   7  ,   "CANAL_ERROR_CHANNEL"           },  // Invalid channel
                {   8  ,   "CANAL_ERROR_FIFO_EMPTY"        },  // FIFO is empty
                {   9  ,   "CANAL_ERROR_FIFO_FULL"         },  // FIFI is full
                {   10 ,   "CANAL_ERROR_FIFO_SIZE"         },  // FIFO size error
                {   11 ,   "CANAL_ERROR_FIFO_WAIT"         },  
                {   12 ,   "CANAL_ERROR_GENERIC"           },  // Generic error
                {   13 ,   "CANAL_ERROR_HARDWARE"          },  // Hardware error
                {   14 ,   "CANAL_ERROR_INIT_FAIL"         },  // Initialization failed
                {   15 ,   "CANAL_ERROR_INIT_MISSING"      },   
                {   16 ,   "CANAL_ERROR_INIT_READY"        },   
                {   17 ,   "CANAL_ERROR_NOT_SUPPORTED"     },   // Not supported
                {   18 ,   "CANAL_ERROR_OVERRUN"           },   // Overrun
                {   19 ,   "CANAL_ERROR_RCV_EMPTY"         },   // Receive buffer empty
                {   20 ,   "CANAL_ERROR_REGISTER"          },   // Register value error
                {   21 ,   "CANAL_ERROR_TRM_FULL"          },   
                {   22 ,   "CANAL_ERROR_ERRFRM_STUFF"      },   // Errorframe: stuff error detected
                {   23 ,   "CANAL_ERROR_ERRFRM_FORM"       },   // Errorframe: form error detected
                {   24 ,   "CANAL_ERROR_ERRFRM_ACK"        },   // Errorframe: acknowledge error
                {   25 ,   "CANAL_ERROR_ERRFRM_BIT1"       },   // Errorframe: bit 1 error
                {   26 ,   "CANAL_ERROR_ERRFRM_BIT0"       },   // Errorframe: bit 0 error
                {   27 ,   "CANAL_ERROR_ERRFRM_CRC"        },   // Errorframe: CRC error
                {   28 ,   "CANAL_ERROR_LIBRARY"           },   // Unable to load library
                {   29 ,   "CANAL_ERROR_PROCADDRESS"       },   // Unable get library proc address
                {   38 ,   "CANAL_ERROR_USER"              },   // Login error
                {   30 ,   "CANAL_ERROR_ONLY_ONE_INSTANCE" },   // Only one instance allowed
                {   31 ,   "CANAL_ERROR_SUB_DRIVER"        },   // Problem with sub driver call
                {   32 ,   "CANAL_ERROR_TIMEOUT"           },   // Blocking call timeout
                {   33 ,   "CANAL_ERROR_NOT_OPEN"          },   // The device is not open.
                {   34 ,   "CANAL_ERROR_PARAMETER"         },   // A parameter is invalid.
                {   35 ,   "CANAL_ERROR_MEMORY"            },   // Memory exhausted.
                {   36 ,   "CANAL_ERROR_INTERNAL"          },   // Some kind of internal program error
                {   37 ,   "CANAL_ERROR_COMMUNICATION"     },   // Some kind of communication error
            };

            public SortedDictionary<int, string> baudrates = new SortedDictionary<int, string>()
            {
                /// Communicaton speeds
                {  0  ,  "0"      },      // User specified (In CANAL i/f DLL).
                {  1  ,  "1000"   },      //   1 Mbit
                {  2  ,  "800"    },      // 800 Kbit
                {  3  ,  "500"    },      // 500 Kbit
                {  4  ,  "250"    },      // 250 Kbit
                {  5  ,  "125"    },      // 125 Kbit
                {  6  ,  "100"    },      // 100 Kbit
                {  7  ,  "50"     },      //  50 Kbit
                {  8  ,  "20"     },      //  20 Kbit
                {  9  ,  "10"     },      //  10 Kbit			

            };
            #endregion

            #region Methods

            #region DLL Imports
            [DllImport(@"C:\\Users\\huqui\\Documents\\Personal\\CANSTUFF\\USB2CAN\\usb2can.dll")]
            public static extern long CanalOpen(string pConfigStr, long flags);
            [DllImport(@"C:\\Users\\huqui\\Documents\\Personal\\CANSTUFF\\USB2CAN\\usb2can.dll")]
            public static extern int CanalClose(long handle);
            #endregion

            #region DLL Function Wrappers
            public long canwrap_CanalOpen(string x, long flag)
            {
                return CanalOpen("asdads", 0x0);
            }

            public int canwrap_CanalClose(long handle)
            {
                return CanalClose(handle);
            }
            #endregion

            #endregion

        }
        CanWrap canal = new CanWrap();

        

        public Form1()
        {
            InitializeComponent();

            InitializeCanalComponents();
        }


        long CanalHandle;
        string CanalBaudRate;
        string SerialNumber;
        long CanalConnectionFlags;


        private void InitializeCanalComponents()
        {
            SerialNumber = textBoxSerialNumber.Text;

            comboBoxBaudRates.SelectedIndex = 4;
        }


        private void buttonCanalOpen_Click(object sender, EventArgs e)
        {

            string connection_string = SerialNumber + " ; " + CanalBaudRate;

            Console.WriteLine("Connecting: \"" + connection_string + "\"");

            if ((CanalHandle = canal.canwrap_CanalOpen(connection_string, CanalConnectionFlags)) <= 0)
            {
                Console.WriteLine("Failed to open CAN Line; Handle: " + CanalHandle);
            }
            else
            {
                Console.WriteLine("Succesfully opened CAN Line; Handle: " + CanalHandle);
            }
        }

        private void buttonCanalClose_Click(object sender, EventArgs e)
        {
            int code;
            code = canal.canwrap_CanalClose(CanalHandle);
            if (canal.error_codes.ContainsKey(code))
            {
                Console.WriteLine(canal.error_codes[code]);
            }
            else
            {
                Console.WriteLine("Unknown Error Code");
            }
        }

        private void comboBoxBaudRates_SelectedIndexChanged(object sender, EventArgs e)
        {
            // Saves the current selected baudrate register code
            //
            if (canal.baudrates.ContainsKey(comboBoxBaudRates.SelectedIndex))
            {
                CanalBaudRate = canal.baudrates[comboBoxBaudRates.SelectedIndex];
            }
            else
            {
                Console.WriteLine("Invalid Baud Rate");
            }

            
        }

        private void textBoxSerialNumber_TextChanged(object sender, EventArgs e)
        {
            SerialNumber = textBoxSerialNumber.Text;
        }


    }
}
