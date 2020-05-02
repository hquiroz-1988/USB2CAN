using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Data;
using System.Runtime.InteropServices;

namespace CanalWrapper
{


    public struct CanalMsg
    {
        public uint flags;
        public uint obid;
        public uint id;
        public byte sizeData;
        public byte[] data;
        public uint timestamp;
    }

    public static class Canal
    {


        #region Structures
        [StructLayout(LayoutKind.Sequential, Pack = 1)]
        private struct structCanalMsg
        {
            public uint flags;
            public uint obid;
            public uint id;
            public byte sizeData;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]
            public byte[] data;
            public uint timestamp;
        }

        #endregion

        #region Delegates
        /// Error Codes
        public static SortedDictionary<int, string> error_codes = new SortedDictionary<int, string>() {
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

        public static SortedDictionary<int, string> baudrates = new SortedDictionary<int, string>()
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

        //[DllImport(@"C:\\Users\\huqui\\Documents\\Personal\\USB2CAN\\CANSTUFF\\USB2CAN\\usb2can.dll", CharSet = CharSet.Ansi)]
        //private static extern long CanalOpen([MarshalAs(UnmanagedType.LPStr)] string pConfigStr, long flags);

        [DllImport(@"C:\\Users\\huqui\\Documents\\Personal\\USB2CAN\\CANSTUFF\\USB2CAN\\usb2can.dll")]
        private static extern long CanalOpen(ref string pConfigStr, long flags);


        [DllImport(@"C:\\Users\\huqui\\Documents\\Personal\\USB2CAN\\CANSTUFF\\USB2CAN\\usb2can.dll")]
        private static extern int CanalClose(long handle);



        [DllImport(@"C:\\Users\\huqui\\Documents\\Personal\\USB2CAN\\CANSTUFF\\USB2CAN\\usb2can.dll")]
        private static extern int CanalBlockingSend(long handle, ref structCanalMsg x, uint timeout);
        #endregion

        #region DLL Function Wrappers
        public static long canwrap_CanalOpen(string x, long flag)
        {
            string str = "ED000200;250";
            return CanalOpen(ref str, 0x0);
        }

        public static int canwrap_CanalClose(long handle)
        {
            return CanalClose(handle);
        }

        public static int canalBlockingSend(long handle, CanalMsg message, uint timeout){
            structCanalMsg msg;
            msg.data = new byte[8];

            msg.flags = message.flags;
            msg.id = message.id;
            msg.obid = message.obid;
            msg.sizeData = message.sizeData;
            msg.timestamp = message.timestamp;

            for (uint i = 0; i < 8; ++i)
            {
                msg.data[i] = 0;
            }

            for (uint i = 0; i < message.sizeData; ++i)
            {
                msg.data[i] = message.data[i];
            }
            Console.WriteLine(handle);
            return CanalBlockingSend(handle, ref msg, timeout);
        }
        #endregion

        #endregion
    }
}
